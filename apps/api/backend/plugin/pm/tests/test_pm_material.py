"""PM 材料主数据 CRUD：接口路径、字段形状、source_id 幂等冲突、逻辑删除。

盯的是三件「过了但不对」的事：

- **路径是 `/api/v1/sys/pm/materials`，不是 `/api/v1/pm/materials`** —— 扩展级插件的
  `[api.pm] prefix = "/pm"` 挂在 admin 的 `/sys` 路由下（同 WIR 那条坑）
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

PM_MATERIALS = '/sys/pm/materials'

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


def test_openapi_paths_live_under_sys() -> None:
    """扩展级插件的最终路径多一层 `/sys` —— 照 `plugin.toml` 的 prefix 拼会 404。"""
    from backend.main import app

    paths = app.openapi()['paths']
    assert '/api/v1/sys/pm/materials' in paths
    assert '/api/v1/sys/pm/materials/{pk}' in paths
    assert '/api/v1/pm/materials' not in paths
