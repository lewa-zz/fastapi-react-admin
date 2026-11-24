"""PM 材料主数据 CRUD：接口路径、字段形状、source_id 幂等冲突、逻辑删除。

盯的是三件「过了但不对」的事：

- **路径是 `/api/v1/sys/materials`** —— 扩展级插件，prefix="/materials" 挂在 /sys 下（同 WIR）
- **列表不能 500（`MissingGreenlet`）** —— `PmMaterial` 刻意没有 relationship，
  有的话 `paging_data()` 序列化时会惰性加载、asyncpg 已经离开 greenlet 上下文
- **`source_id` 撞了报 409**，不是 500：它是导入幂等键（唯一约束 `(source_id, deleted)`）

⚠️ 接口的删除是**逻辑删除**，`source_id` 的唯一约束还占着 —— 所以收尾必须硬删，
不能靠接口删（同 `plugin/wir/tests/test_wir_import.py` 的 `purge()`）。
"""

import asyncio

from collections.abc import Iterator
from decimal import Decimal

import pytest

from sqlalchemy import text
from starlette.testclient import TestClient

from backend.database.db import create_database_async_engine, create_database_async_session, get_database_url

PM_MATERIALS = '/sys/materials'

#: 造一条材料（字段取真实 Excel 的形状：`台/件` 是实测单位之一）
MATERIAL = {
    'source_id': 900001,
    'kind': 'PLC',
    'category': 'BMS控制柜',
    'name_cn': '测试控制器',
    'name_en': 'Test Controller',
    'unit': '台/件',
    'price': '1015.6250',
}


def purge() -> None:
    """硬删这张表：接口的删除是逻辑删除，`source_id` 还占着唯一性。"""

    async def _run() -> None:
        engine = create_database_async_engine(get_database_url(unittest=True))
        session_maker = create_database_async_session(engine)
        try:
            async with session_maker.begin() as session:
                await session.execute(text('DELETE FROM pm_material'))
        finally:
            await engine.dispose()

    asyncio.run(_run())


@pytest.fixture(autouse=True)
def _clean_pm_material() -> Iterator[None]:
    purge()
    yield
    purge()


def create_material(client: TestClient, headers: dict[str, str], **overrides: object) -> dict:
    payload = {**MATERIAL, **overrides}
    res = client.post(PM_MATERIALS, headers=headers, json=payload)
    assert res.status_code == 200, res.text
    body = res.json()
    assert body['code'] == 200, body
    return body['data']


def test_create_material(client: TestClient, token_headers: dict[str, str]) -> None:
    data = create_material(client, token_headers)

    assert data['kind'] == 'PLC'
    assert data['category'] == 'BMS控制柜'
    assert data['name_cn'] == '测试控制器'
    assert data['name_en'] == 'Test Controller'
    assert data['unit'] == '台/件'
    assert data['source_id'] == 900001
    # 金额是 `Numeric(14, 4)`，下发的形状跟着 pydantic 走（Decimal → 字符串），值必须精确
    assert Decimal(str(data['price'])) == Decimal('1015.6250')
    # 两个新列的默认值：不传也要落到库里
    assert data['currency'] == 'RMB'
    assert data['active'] is True
    # `id` 是雪花，序列化成字符串（前端不许 Number() 它）
    assert isinstance(data['id'], str)


def test_list_materials_returns_the_row(client: TestClient, token_headers: dict[str, str]) -> None:
    created = create_material(client, token_headers)

    res = client.get(PM_MATERIALS, headers=token_headers)
    assert res.status_code == 200, res.text
    body = res.json()
    assert body['code'] == 200, body
    data = body['data']
    assert data['total'] == 1
    assert [item['id'] for item in data['items']] == [created['id']]
    assert data['items'][0]['name_cn'] == '测试控制器'


@pytest.mark.parametrize(
    ('params', 'expected_total'),
    [
        ({'search': '测试控制器'}, 1),
        ({'search': 'Test Controller'}, 1),
        ({'kind': 'PLC'}, 1),
        ({'category': 'BMS控制柜'}, 1),
        ({'kind': 'Sensor（现场安装）'}, 0),
        ({'active': 'true'}, 1),
        ({'active': 'false'}, 0),
    ],
)
def test_list_filters(
    client: TestClient, token_headers: dict[str, str], params: dict[str, str], expected_total: int
) -> None:
    create_material(client, token_headers)

    res = client.get(PM_MATERIALS, headers=token_headers, params=params)
    assert res.status_code == 200, res.text
    body = res.json()
    assert body['code'] == 200, body
    assert body['data']['total'] == expected_total, params


def test_update_material(client: TestClient, token_headers: dict[str, str]) -> None:
    created = create_material(client, token_headers)

    res = client.put(f'{PM_MATERIALS}/{created["id"]}', headers=token_headers, json={'name_cn': '测试控制器（改）'})
    assert res.status_code == 200, res.text
    assert res.json()['code'] == 200

    detail = client.get(f'{PM_MATERIALS}/{created["id"]}', headers=token_headers)
    assert detail.status_code == 200, detail.text
    assert detail.json()['data']['name_cn'] == '测试控制器（改）'


def test_update_to_an_occupied_source_id_is_a_conflict(client: TestClient, token_headers: dict[str, str]) -> None:
    """`source_id` 的唯一性在**更新**路径上也要拦（不只是创建）

    service 里那条分支只在「改成别人的 source_id」时才走到 —— 不测的话，
    表现是 500（撞库唯一约束）或者静默写成两条同源行，两种都不在这条用例之外暴露。
    """
    first = create_material(client, token_headers)
    second = create_material(client, token_headers, source_id=900002, name_cn='第二条')

    res = client.put(f'{PM_MATERIALS}/{second["id"]}', headers=token_headers, json={'source_id': 900001})
    assert res.status_code == 409, res.text
    assert res.json()['code'] == 409

    # 409 之后那条记录本身没被改（事务回滚 / 根本没写进去）
    detail = client.get(f'{PM_MATERIALS}/{second["id"]}', headers=token_headers).json()['data']
    assert detail['source_id'] == 900002
    assert detail['name_cn'] == '第二条'
    assert detail['id'] != first['id']


def test_update_keeping_its_own_source_id_is_not_a_conflict(client: TestClient, token_headers: dict[str, str]) -> None:
    """把**自己**的 `source_id` 原样带回来（前端整表单提交）不能报 409"""
    created = create_material(client, token_headers)

    res = client.put(
        f'{PM_MATERIALS}/{created["id"]}',
        headers=token_headers,
        json={'source_id': 900001, 'memo': '整表单提交'},
    )
    assert res.status_code == 200, res.text
    assert res.json()['code'] == 200

    detail = client.get(f'{PM_MATERIALS}/{created["id"]}', headers=token_headers).json()['data']
    assert detail['source_id'] == 900001
    assert detail['memo'] == '整表单提交'
    # 部分更新：没传的字段保持原值
    assert detail['name_cn'] == '测试控制器'
    assert detail['unit'] == '台/件'


@pytest.mark.parametrize(
    ('field', 'length', 'column_limit'),
    [
        ('name_en', 257, 256),  # UniversalStr(256)
        ('kind', 65, 64),  # UniversalStr(64)
        ('unit', 33, 32),  # UniversalStr(32)
    ],
)
def test_overlong_field_is_a_422_naming_the_column(
    client: TestClient, token_headers: dict[str, str], field: str, length: int, column_limit: int
) -> None:
    """`ColumnLengthChecked` 从模型列现读上限 —— 超长报 422 且带字段名，不是裸 SQL 500

    判据和 `app/admin/tests/api_v1/test_column_length_gate.py` 同一套：状态码之外
    还必须点出**字段名 + 上限**，否则一个「把所有请求都拒掉」的实现也是绿的。
    """
    res = client.post(PM_MATERIALS, headers=token_headers, json={**MATERIAL, field: 'x' * length})
    assert res.status_code == 422, res.text
    body = res.json()
    assert body['code'] == 422, body
    msg = body['msg']
    assert field in msg, f'报错没点出是哪个字段：{msg}'
    assert str(column_limit) in msg, f'报错没给出上限（列长度 {column_limit}）：{msg}'


@pytest.mark.parametrize(('field', 'column_limit'), [('name_en', 256), ('kind', 64), ('unit', 32)])
def test_value_exactly_at_the_column_limit_is_accepted(
    client: TestClient, token_headers: dict[str, str], field: str, column_limit: int
) -> None:
    """正好等于上限要放过 —— 判据写成 `>=` 会把恰好填满的值拒掉，而那种误杀在界面上表现为「明明没超还是存不下」"""
    created = create_material(client, token_headers, **{field: 'x' * column_limit})
    assert created[field] == 'x' * column_limit


def test_spec_longer_than_a_varchar_is_accepted(client: TestClient, token_headers: dict[str, str]) -> None:
    """`spec` 是 `UniversalText`：实测源 Excel 里有 286 字符且含换行的规格，不该被截断/拒绝"""
    spec = ('第一行规格描述；' * 40) + '\n' + ('第二行继续描述；' * 20)
    created = create_material(client, token_headers, spec=spec)

    detail = client.get(f'{PM_MATERIALS}/{created["id"]}', headers=token_headers).json()['data']
    assert detail['spec'] == spec
    assert '\n' in detail['spec']


def test_duplicate_source_id_is_a_conflict(client: TestClient, token_headers: dict[str, str]) -> None:
    created = create_material(client, token_headers)

    res = client.post(PM_MATERIALS, headers=token_headers, json={**MATERIAL, 'name_cn': '同名来源的另一条'})
    assert res.status_code == 409, res.text
    assert res.json()['code'] == 409
    # 撞了之后库里还是只有那一条
    page = client.get(PM_MATERIALS, headers=token_headers).json()['data']
    assert page['total'] == 1
    assert page['items'][0]['id'] == created['id']


def test_delete_material_is_logical(client: TestClient, token_headers: dict[str, str]) -> None:
    created = create_material(client, token_headers)

    res = client.request('DELETE', PM_MATERIALS, headers=token_headers, json={'pks': [created['id']]})
    assert res.status_code == 200, res.text
    assert res.json()['code'] == 200

    detail = client.get(f'{PM_MATERIALS}/{created["id"]}', headers=token_headers)
    assert detail.status_code == 404, detail.text

    page = client.get(PM_MATERIALS, headers=token_headers).json()['data']
    assert page['total'] == 0


def test_detail_of_unknown_material_is_404(client: TestClient, token_headers: dict[str, str]) -> None:
    res = client.get(f'{PM_MATERIALS}/2049629108299009999', headers=token_headers)
    assert res.status_code == 404, res.text
    assert res.json()['code'] == 404


# ── 卡片点名的另外六件事：落库形状、active 语义、软删后的 source_id、Decimal ──────────

#: 金额 / 数量六列：`Numeric(14, 4)`，整数值上界 10 位 + 4 位小数
MONEY = {
    'qty': '3.5000',
    'price': '0.0001',  # 4 位小数能表示的最小非零值
    'contract_price': '1234567890.1234',  # 14 位有效数字的边界
    'in_price': '999999.9999',
    'out_price': '1.0000',
    'market_price': '0.1000',
}

MONEY_COLUMNS = tuple(MONEY)


def fetch_rows(sql: str, **params: object) -> list[dict[str, object]]:
    """直接查**测试库**，绕过接口看落库的真实形状

    和 `purge()` 同一个开法（每次新建引擎 + `asyncio.run`）：复用全局
    `async_test_engine` 会和 TestClient 自己的事件循环打架
    （`got Future attached to a different loop`）。
    """

    async def _run() -> list[dict[str, object]]:
        engine = create_database_async_engine(get_database_url(unittest=True))
        session_maker = create_database_async_session(engine)
        try:
            async with session_maker.begin() as session:
                result = await session.execute(text(sql), params)
                return [dict(row._mapping) for row in result]
        finally:
            await engine.dispose()

    return asyncio.run(_run())


def soft_delete(client: TestClient, headers: dict[str, str], *pks: str) -> None:
    res = client.request('DELETE', PM_MATERIALS, headers=headers, json={'pks': list(pks)})
    assert res.status_code == 200, res.text
    assert res.json()['code'] == 200, res.text


def test_create_without_source_id_leaves_it_null(client: TestClient, token_headers: dict[str, str]) -> None:
    """`source_id` 可空 —— 手工新增的材料没有源 Excel 行 ID

    两个断言必须一起成立：
    - 不传就是 **NULL**，不是 0 / 空串（否则会和「源表 ID = 0」那条撞成同一个业务键）
    - **第二条不传 `source_id` 的也要插得进去**：`(source_id, deleted)` 上的唯一性对 NULL
      必须放行（PG / MySQL 认为 NULL 互不相等；SQL Server 靠模型 / 迁移里那条
      `source_id IS NOT NULL` 的筛选唯一索引）。收紧成普通唯一约束的话，
      第二份手工材料会静默报 409。
    """
    payload = {key: value for key, value in MATERIAL.items() if key != 'source_id'}

    first = client.post(PM_MATERIALS, headers=token_headers, json=payload)
    assert first.status_code == 200, first.text
    first_data = first.json()['data']
    assert first_data['source_id'] is None
    # 不传 currency / active 也要落到模型的默认值
    assert first_data['currency'] == 'RMB'
    assert first_data['active'] is True

    second = client.post(PM_MATERIALS, headers=token_headers, json={**payload, 'name_cn': '第二条手工材料'})
    assert second.status_code == 200, second.text
    assert second.json()['data']['id'] != first_data['id']

    detail = client.get(f'{PM_MATERIALS}/{first_data["id"]}', headers=token_headers)
    assert detail.status_code == 200, detail.text
    assert detail.json()['data']['source_id'] is None

    rows = fetch_rows('SELECT id FROM pm_material WHERE source_id IS NULL')
    assert len(rows) == 2, '两条都没有 source_id 的材料应该都落在库里'


def test_soft_deleted_row_keeps_its_own_id_in_deleted_and_a_timestamp(
    client: TestClient, token_headers: dict[str, str]
) -> None:
    """软删不是 `DELETE`：行还在，`deleted` 存**这一行自己的 id**，`deleted_time` 有值

    ⚠️ 卡片写的是「`deleted=True`」，而仓库的 `LogicalDeleteMixin` 是「0：否；id：是」
    （`apps/api/AGENTS.md` 硬纪律那条）。按**这一行自己的 id** 断言，顺带钉住
    「同一个 `source_id` 软删之后还能再插」的机制（见下一条）。
    """
    created = create_material(client, token_headers)
    soft_delete(client, token_headers, created['id'])

    # 默认列表恒过滤 `deleted=0`，详情也查不到
    page = client.get(PM_MATERIALS, headers=token_headers).json()['data']
    assert page['total'] == 0
    assert client.get(f'{PM_MATERIALS}/{created["id"]}', headers=token_headers).status_code == 404

    rows = fetch_rows('SELECT id, deleted, deleted_time FROM pm_material WHERE id = :pk', pk=int(created['id']))
    assert len(rows) == 1, '软删把行真的删掉了 —— 那就没法再插同一个 source_id'
    row = rows[0]
    assert row['deleted'] == int(created['id']), f'deleted 应该是这一行自己的 id，实际是 {row["deleted"]!r}'
    assert row['deleted_time'] is not None, 'deleted_time 没写'


def test_inactive_material_is_listed_by_default_and_is_filterable(
    client: TestClient, token_headers: dict[str, str]
) -> None:
    """停用（`active=false`）≠ 删除：默认列表照样看得到，`?active=` 两个值各取各的

    卡片点名这条是因为两种错法都「看起来对」：默认把停用的过滤掉（候选里少了一条，
    没人报错），或者 `active` 入参根本没生效（筛选框点了没反应）。
    """
    created = create_material(client, token_headers, active=False)
    assert created['active'] is False

    # 不传 active = 全部（停用的也在里面）
    page = client.get(PM_MATERIALS, headers=token_headers).json()['data']
    assert page['total'] == 1
    assert page['items'][0]['active'] is False

    inactive = client.get(PM_MATERIALS, headers=token_headers, params={'active': 'false'}).json()['data']
    assert inactive['total'] == 1
    assert inactive['items'][0]['id'] == created['id']

    only_active = client.get(PM_MATERIALS, headers=token_headers, params={'active': 'true'}).json()['data']
    assert only_active['total'] == 0

    detail = client.get(f'{PM_MATERIALS}/{created["id"]}', headers=token_headers)
    assert detail.status_code == 200, detail.text
    assert detail.json()['data']['active'] is False


def test_source_id_can_be_reused_after_soft_delete(client: TestClient, token_headers: dict[str, str]) -> None:
    """唯一约束是 `(source_id, deleted)`，不是 `source_id` —— 软删之后同一个 source_id 可以再插

    反过来说：谁要是把它改成只约束 `source_id`，这条会红。而那种错的症状是
    「导入的材料表里删掉一行、再导一次就 409」—— 用户只会看到「这条已经存在」，
    而界面上根本找不到它。
    """
    first = create_material(client, token_headers, source_id=900123)
    soft_delete(client, token_headers, first['id'])

    second = create_material(client, token_headers, source_id=900123, name_cn='软删后重建')
    assert second['source_id'] == 900123
    assert second['id'] != first['id']

    page = client.get(PM_MATERIALS, headers=token_headers).json()['data']
    assert page['total'] == 1
    assert page['items'][0]['id'] == second['id']

    rows = fetch_rows('SELECT id, deleted, deleted_time FROM pm_material WHERE source_id = :sid', sid=900123)
    assert len(rows) == 2, '软删的那一行应该还在库里（软删不是删）'
    assert {row['deleted'] for row in rows} == {0, int(first['id'])}


def test_decimal_fields_round_trip_without_losing_precision(client: TestClient, token_headers: dict[str, str]) -> None:
    """六个金额 / 数量列的 Decimal 往返：值不能变，**标度（末尾的 0）也不能丢**

    写成 `float` 的话 `1.0000` 会变成 `1.0`、`1234567890.1234` 在 SQL Server 的
    `DOUBLE PRECISION` 上还会被舍入 —— 而金额差一分钱在报价里是真金白银。
    所以这里走**详情接口**（读的是库里的值，不是刚 post 进去的那个 Python 对象）。
    """
    created = create_material(client, token_headers, **MONEY)

    detail = client.get(f'{PM_MATERIALS}/{created["id"]}', headers=token_headers).json()['data']
    for name, raw in MONEY.items():
        assert Decimal(str(detail[name])) == Decimal(raw), f'{name} 的值变了：{detail[name]!r} != {raw!r}'
        # pydantic 把 Decimal 序列化成字符串；标度丢了说明中间过了 float
        assert str(detail[name]) == raw, f'{name} 的标度丢了：{detail[name]!r} != {raw!r}'

    # 库里的原始值也是 Decimal（asyncpg / pyodbc / asyncmy 对 NUMERIC 都返回 Decimal）
    rows = fetch_rows(f'SELECT {", ".join(MONEY)} FROM pm_material WHERE id = :pk', pk=int(created['id']))
    assert len(rows) == 1
    for name, raw in MONEY.items():
        assert isinstance(rows[0][name], Decimal), f'{name} 从库里读回来是 {type(rows[0][name])!r}'
        assert rows[0][name] == Decimal(raw), f'{name} 落库时变了：{rows[0][name]!r}'


def test_money_columns_are_numeric_14_4_and_never_float() -> None:
    """金额 / 数量六列：模型、测试库、三种方言的编译产物**都是 `NUMERIC(14, 4)`**

    🔴 `Mapped[float]` 从 SQLAlchemy 2.1 起映射成 `Double`（不是 `Float`）——SQL Server 上
    等于把金额存成二进制浮点，`test_model_matches_migrations` 会红，而 **CI 的
    `pytest · SQL Server` job 是唯一能当场拦住的地方**：本机 PG 上 `Float` 和 `Double`
    都落 `double precision`，比不出差别（`alembic` 分册里 `cost_time` 那次）。
    所以三层都断言一遍，本机就能拦下「改回 Mapped[float]」。
    """
    from sqlalchemy import Float, Numeric, create_engine, inspect
    from sqlalchemy.dialects import mssql, mysql, postgresql

    from backend.plugin.materials.model.material import PmMaterial

    for name in MONEY_COLUMNS:
        column_type = PmMaterial.__table__.c[name].type
        assert isinstance(column_type, Numeric), f'模型里 {name} 是 {column_type!r}，不是 Numeric'
        assert not isinstance(column_type, Float), f'模型里 {name} 被映射成了浮点：{column_type!r}'
        assert (column_type.precision, column_type.scale) == (14, 4), f'模型里 {name} 是 {column_type!r}'
        for dialect in (postgresql.dialect(), mysql.dialect(), mssql.dialect()):
            compiled = column_type.compile(dialect=dialect)
            assert compiled.replace(' ', '').upper() == 'NUMERIC(14,4)', f'{dialect.name} 上 {name} 编译成 {compiled!r}'

    # 库上的真实列类型（`fba_test` 是 `create_all` 按模型建的，这里是模型→DDL 的闭环）
    url = get_database_url(unittest=True).render_as_string(hide_password=False)
    sync_url = url.replace('+asyncpg', '+psycopg').replace('+aioodbc', '+pyodbc').replace('+asyncmy', '+pymysql')
    engine = create_engine(sync_url, future=True)
    try:
        with engine.connect() as conn:
            columns = {column['name']: column['type'] for column in inspect(conn).get_columns('pm_material')}
    finally:
        engine.dispose()

    for name in MONEY_COLUMNS:
        db_type = columns[name]
        assert isinstance(db_type, Numeric), f'库上 {name} 是 {db_type!r}，不是 Numeric'
        assert not isinstance(db_type, Float), f'库上 {name} 是浮点：{db_type!r}'
        assert (db_type.precision, db_type.scale) == (14, 4), f'库上 {name} 是 {db_type!r}'


def test_openapi_paths() -> None:
    """扩展级插件路径多一层 `/sys` —— 同 WIR。"""
    from backend.main import app

    paths = app.openapi()['paths']
    assert '/api/v1/sys/materials' in paths
    assert '/api/v1/sys/materials/{pk}' in paths
    assert '/api/v1/materials' not in paths
