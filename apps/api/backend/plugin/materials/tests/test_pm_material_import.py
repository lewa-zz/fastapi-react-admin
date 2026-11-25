"""PM 材料的 Excel 导入 / 导出。

盯的是「导进去了但不对」那一类，它们都不报错：

- **源表的表头认不出来**（`type` / `mat_CN` / `amo` / 带制表符的 `\\tunit`）——
  非必填列拼错是纯静默的，那一列数据全丢；整份文件照样解析成功
- **`source_id` 不是幂等键**：同一份材料表导两次就多一份行，而 `(source_id, deleted)`
  上有唯一约束，第二次本该报冲突
- **金额过了 `float`**：`Numeric(14, 4)` 上的差一分钱是真金白银
- **导出没有按筛选取数 / 没有列翻译**：文件生成了，列名是一串 `export.column.xxx`

⚠️ 接口的删除是逻辑删除，`source_id` 的唯一性还占着 —— 所以收尾必须硬删
（同 `plugin/wir/tests/test_wir_import.py` 的 `purge()`）。
"""

import asyncio
import io

from collections.abc import Iterator
from decimal import Decimal
from typing import Any

import pytest
import yaml

from openpyxl import Workbook, load_workbook
from sqlalchemy import text
from starlette.testclient import TestClient

from backend.core.path_conf import LOCALE_DIR
from backend.database.db import create_database_async_engine, create_database_async_session, get_database_url

MATERIALS = '/sys/materials'
IMPORT = '/sys/materials/import'
EXPORT = '/sys/materials/export'
EXPORTS = '/sys/exports'

XLSX = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'

#: 桌面 `材料表.xlsx` 的真实表头（`plugin/materials/AGENTS.md` 那张表）。
#: `\\tunit` 是第 10 列的原样表头 —— 带一个制表符
SOURCE_HEADER = [
    'id',
    'type',
    'Category',
    'mat_CN',
    'mat_EN',
    'model',
    'spec',
    'brand',
    'amo',
    '\tunit',
    'price',
    'contract_price',
    'in_price',
    'out_price',
    'market_price',
    'memo',
]

#: 第一行的金额刻意选「末端有 4 位小数」的值：过一手 float 就看不出来了
ROW_ONE = [
    1,
    'PLC',
    'BMS控制柜',
    '控制器',
    'Controller',
    'S7-1200',
    '多行规格\n第二行',
    'Siemens',
    2.5,
    '台/件',
    1015.625,
    2539.0625,
    980.5,
    1100.25,
    1200.125,
    '备注一',
]

ROW_TWO = [
    2,
    'Sensor（现场安装）',
    'BMS控制柜',
    '温度传感器',
    'Temperature Sensor',
    None,
    '0-10V',
    'Schneider',
    3,
    '套',
    88.0,
    264.0,
    None,
    None,
    None,
    None,
]


def build_source_xlsx(header: list[str] | None = None, rows: list[list[Any]] | None = None) -> bytes:
    """按源文件的样子造一份：sheet 叫 `Material`，表头是业务系统的原表头"""
    wb = Workbook()
    ws = wb.worksheets[0]
    ws.title = 'Material'
    ws.append(header if header is not None else SOURCE_HEADER)
    for row in rows if rows is not None else [ROW_ONE, ROW_TWO]:
        ws.append(row)
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


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


def fetch_rows(sql: str, **params: object) -> list[dict[str, object]]:
    """直接查**测试库**，绕过接口看落库的真实形状（同 `test_pm_material.py`）"""

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


@pytest.fixture(autouse=True)
def _clean_materials() -> Iterator[None]:
    purge()
    yield
    purge()


def upload(client: TestClient, headers: dict[str, str], raw: bytes, mode: str = 'create') -> dict:
    res = client.post(
        f'{IMPORT}/preview?mode={mode}',
        headers=headers,
        files={'file': ('材料表.xlsx', raw, XLSX)},
    )
    assert res.status_code == 200, res.text
    body = res.json()
    assert body['code'] == 200, body
    return body['data']


def commit(client: TestClient, headers: dict[str, str], token: str) -> dict:
    res = client.post(
        f'{IMPORT}/commit',
        headers=headers,
        json={'import_token': token, 'exclude_rows': [], 'atomic': False},
    )
    assert res.status_code == 200, res.text
    body = res.json()
    assert body['code'] == 200, body
    return body['data']


def export(client: TestClient, headers: dict[str, str], body: dict[str, Any] | None = None) -> dict[str, Any]:
    res = client.post(EXPORT, headers=headers, json=body or {})
    payload = res.json()
    assert res.status_code == payload['code'] or payload['code'] == 200, res.text
    return payload


def download(client: TestClient, headers: dict[str, str], job_id: str) -> bytes:
    res = client.get(f'{EXPORTS}/{job_id}/download', headers=headers)
    assert res.status_code == 200, res.text
    return res.content


def sheet_rows(raw: bytes) -> tuple[list[str], list[list[Any]]]:
    ws = load_workbook(io.BytesIO(raw)).worksheets[0]
    rows = [list(row) for row in ws.iter_rows(values_only=True)]
    return [str(cell) for cell in rows[0]], rows[1:]


def route_guards(path: str) -> tuple[list[str], bool]:
    """这条路由上挂了哪些 `RequestPermission` 码、有没有 `DependsRBAC`

    直接看**插件自己的 router**：`app.routes` 里只有 11 条（API 挂在 Mount 下面），
    遍历它一个材料路径都找不到 —— 那种「什么都没扫到」会让断言假绿。
    """
    from backend.common.security.permission import RequestPermission
    from backend.plugin.materials.api.v1.sys.materials import router

    codes: list[str] = []
    has_rbac = False

    for route in router.routes:
        if getattr(route, 'path', None) != path:
            continue
        dependencies = [getattr(dependency, 'dependency', None) for dependency in route.dependencies or []]
        codes.extend(item.value for item in dependencies if isinstance(item, RequestPermission))
        has_rbac = has_rbac or any(getattr(item, '__name__', '') == 'rbac_verify' for item in dependencies)
    if not codes and not has_rbac:
        raise AssertionError(f'路由没找到：{path}')
    return codes, has_rbac


# ═══════════════════════════════ 源表表头 ═══════════════════════════════


def test_source_sheet_headers_are_recognized(client: TestClient, token_headers: dict[str, str]) -> None:
    """`id` / `type` / `mat_CN` / `amo` / `\\tunit` 这些原表头都要认出来

    没认出来的列是**静默丢数据**：整份文件照样解析成功、行数也对，只是那一列全空
    （`ignored_headers` 是唯一能看出来的地方）。
    """
    preview = upload(client, token_headers, build_source_xlsx())

    assert preview['total'] == 2
    assert preview['valid'] == 2
    assert preview['ignored_headers'] == [], '源表的表头没认全 —— 那些列的数据会静默丢掉'

    first = preview['rows'][0]
    # `type` → `kind`、`mat_CN` → `name_cn`、`amo` → `qty`、`\tunit` → `unit`
    assert first['values']['kind'] == 'PLC'
    assert first['values']['name_cn'] == '控制器'
    assert first['values']['qty'] == '2.5'
    assert first['values']['unit'] == '台/件'
    assert first['values']['source_id'] == '1'


def test_clean_unit_header_is_accepted_too(client: TestClient, token_headers: dict[str, str]) -> None:
    """同一个 `unit` 列，模板里是干净的 `unit`：脏表头只是「多认一种写法」，不是唯一写法"""
    header = ['unit' if name == '\tunit' else name for name in SOURCE_HEADER]
    preview = upload(client, token_headers, build_source_xlsx(header=header))

    assert preview['valid'] == 2
    assert preview['ignored_headers'] == []
    assert preview['rows'][0]['values']['unit'] == '台/件'


# ═══════════════════════════════ 导入落库 ═══════════════════════════════


def test_import_creates_rows_and_is_idempotent_on_source_id(client: TestClient, token_headers: dict[str, str]) -> None:
    """同一份材料表导两次不该多一行 —— `source_id` 就是幂等键"""
    raw = build_source_xlsx()

    preview = upload(client, token_headers, raw)
    assert preview['to_create'] == 2
    result = commit(client, token_headers, preview['import_token'])
    assert result['committed'] is True
    assert len(result['created']) == 2

    page = client.get(MATERIALS, headers=token_headers).json()['data']
    assert page['total'] == 2
    ids = {item['source_id'] for item in page['items']}
    assert ids == {1, 2}

    # 再导一遍（upsert）：按 `source_id` 认回同一行，不是又建两条
    again = upload(client, token_headers, raw, mode='upsert')
    assert again['to_update'] == 2
    assert again['to_create'] == 0
    assert commit(client, token_headers, again['import_token'])['committed'] is True

    assert client.get(MATERIALS, headers=token_headers).json()['data']['total'] == 2
    assert len(fetch_rows('SELECT id FROM pm_material')) == 2


def test_create_mode_reports_a_row_that_already_exists(client: TestClient, token_headers: dict[str, str]) -> None:
    """`create` 模式下撞已存在要报出来，不是静默覆盖，也不是等提交时撞唯一约束"""
    raw = build_source_xlsx()
    commit(client, token_headers, upload(client, token_headers, raw)['import_token'])

    preview = upload(client, token_headers, raw, mode='create')
    assert preview['total'] == 2
    assert preview['valid'] == 0
    assert preview['to_create'] == 0
    assert all(not row['ok'] and '已存在' in row['errors'][0] for row in preview['rows'])


def test_update_mode_reports_a_missing_key_and_a_row_without_one(
    client: TestClient, token_headers: dict[str, str]
) -> None:
    """`update` 模式下：认不出的 `source_id` 报「不存在」；连 `id` 都没有的行也说清楚"""
    preview = upload(client, token_headers, build_source_xlsx(), mode='update')
    assert preview['total'] == 2
    assert preview['valid'] == 0
    assert all(not row['ok'] and '不存在' in row['errors'][0] for row in preview['rows'])

    # 第二行去掉 `id`：它认不出要改哪一条，报的是专门那句话
    row_without_id = list(ROW_TWO)
    row_without_id[0] = None
    mixed = upload(client, token_headers, build_source_xlsx(rows=[ROW_ONE, row_without_id]), mode='update')
    second = mixed['rows'][1]
    assert not second['ok']
    assert '来源 ID' in second['errors'][0], second['errors']


def test_update_mode_rewrites_the_existing_row(client: TestClient, token_headers: dict[str, str]) -> None:
    """`update` 真的改的是那一行（不是新建），空白单元格保持原值"""
    raw = build_source_xlsx()
    commit(client, token_headers, upload(client, token_headers, raw)['import_token'])

    changed = list(ROW_ONE)
    changed[3] = '控制器（改）'  # mat_CN
    changed[15] = None  # memo 留空 → 保持原值
    preview = upload(client, token_headers, build_source_xlsx(rows=[changed]), mode='update')
    assert preview['to_update'] == 1
    assert preview['to_create'] == 0
    commit(client, token_headers, preview['import_token'])

    page = client.get(MATERIALS, headers=token_headers).json()['data']
    assert page['total'] == 2
    row = next(item for item in page['items'] if item['source_id'] == 1)
    assert row['name_cn'] == '控制器（改）'
    assert row['memo'] == '备注一', '空白单元格应该保持原值，不是被清空'


def test_money_columns_keep_their_precision(client: TestClient, token_headers: dict[str, str]) -> None:
    """金额 / 数量落库是 `Decimal`：值不能变，**标度**也不能丢

    xlsx 里的数字是 IEEE double，走 `float` 转换会把 `1200.125` 之类截出尾差，
    而 `Numeric(14, 4)` 上差一分钱是真金白银。
    """
    raw = build_source_xlsx()
    commit(client, token_headers, upload(client, token_headers, raw)['import_token'])

    rows = fetch_rows(
        'SELECT qty, price, contract_price, in_price, out_price, market_price FROM pm_material WHERE source_id = 1'
    )
    assert len(rows) == 1
    expected = {
        'qty': Decimal('2.5000'),
        'price': Decimal('1015.6250'),
        'contract_price': Decimal('2539.0625'),
        'in_price': Decimal('980.5000'),
        'out_price': Decimal('1100.2500'),
        'market_price': Decimal('1200.1250'),
    }
    for name, value in expected.items():
        assert isinstance(rows[0][name], Decimal), f'{name} 从库里读回来是 {type(rows[0][name])!r}'
        assert rows[0][name] == value, f'{name} 落库时变了：{rows[0][name]!r} != {value!r}'


def test_a_non_numeric_money_cell_is_a_row_error(client: TestClient, token_headers: dict[str, str]) -> None:
    """填了「1000 元」这种非数字：那一行报错、给出列名和原值，不是整个预览 500"""
    row = list(ROW_ONE)
    row[10] = '一千元'
    preview = upload(client, token_headers, build_source_xlsx(rows=[row]))

    assert preview['valid'] == 0
    error = preview['rows'][0]['errors'][0]
    assert '合同单价' in error, error
    assert '一千元' in error, error


def test_the_downloaded_template_can_be_filled_and_imported(client: TestClient, token_headers: dict[str, str]) -> None:
    """下载模板 → 填两行 → 导回来。模板的表头是当前语言的列名，靠 `label` 的译文认"""
    res = client.get(f'{IMPORT}/template', headers=token_headers)
    assert res.status_code == 200, res.text
    assert res.headers['content-type'].startswith(XLSX)

    wb = load_workbook(io.BytesIO(res.content))
    ws = wb.worksheets[0]
    headers = [str(cell.value) for cell in ws[1]]
    assert '材料中文名' in headers, headers
    index = {name: position + 1 for position, name in enumerate(headers)}

    def cells(**values: Any) -> None:
        row = ws.max_row + 1
        for name, value in values.items():
            ws.cell(row=row, column=index[name], value=value)

    cells(
        类型='PLC',
        类别='BMS控制柜',
        材料中文名='模板材料一',
        材料英文名='Template Material One',
        单位='台/件',
        合同单价=12.5,
    )
    cells(类型='PLC', 类别='BMS控制柜', 材料中文名='模板材料二', 材料英文名='Template Material Two', 单位='套')
    buf = io.BytesIO()
    wb.save(buf)

    preview = upload(client, token_headers, buf.getvalue())
    assert preview['valid'] == 2, preview['rows']
    assert commit(client, token_headers, preview['import_token'])['committed'] is True

    page = client.get(MATERIALS, headers=token_headers).json()['data']
    assert {item['name_cn'] for item in page['items']} == {'模板材料一', '模板材料二'}
    # 模板里没有 `id` 列：这些行只能新增，`source_id` 落 NULL（同 `test_pm_material.py` 那条）
    assert all(item['source_id'] is None for item in page['items'])


# ═══════════════════════════════ 导出 ═══════════════════════════════


def create_material(client: TestClient, headers: dict[str, str], **overrides: Any) -> dict:
    payload = {
        'kind': 'PLC',
        'category': 'BMS控制柜',
        'name_cn': '导出材料',
        'name_en': 'Export Material',
        'unit': '台/件',
        'price': '10.5000',
        **overrides,
    }
    res = client.post(MATERIALS, headers=headers, json=payload)
    assert res.status_code == 200, res.text
    return res.json()['data']


def test_export_writes_the_filtered_rows(client: TestClient, token_headers: dict[str, str]) -> None:
    """导出的是列表接口筛出来的那批（筛选参数同名同义）"""
    kept = create_material(client, token_headers)
    create_material(client, token_headers, kind='Sensor（现场安装）', name_cn='筛掉的材料')

    body = export(client, token_headers, {'filters': {'kind': 'PLC'}})
    assert body['code'] == 200, body
    job = body['data']
    assert job['status'] == 2, job  # 小批量当场生成
    assert job['total'] == job['row_count'] == 1

    header, rows = sheet_rows(download(client, token_headers, job['id']))
    assert header[0] == 'ID'
    assert header[-1] == '更新时间'
    assert len(rows) == 1
    id_position = header.index('ID')
    # 雪花 ID 按文本写：19 位数字在这一步塌掉是不会报错的（硬纪律 6）
    assert rows[0][id_position] == kept['id']


def test_export_rejects_an_unknown_filter(client: TestClient, token_headers: dict[str, str]) -> None:
    """拼错的筛选参数被忽略 = 导出全表，而用户以为是筛过的（`extra='forbid'`）"""
    create_material(client, token_headers)
    body = export(client, token_headers, {'filters': {'categroy': 'BMS控制柜'}})
    assert body['code'] == 400, body
    assert 'categroy' in body['msg'], body


def test_export_columns_are_all_translated() -> None:
    """列名 / 筛选名 / 资源名都是运行时拼的键（`t(column.label)`），`test_i18n.py` 的正则扫不到

    缺键的表现：那门语言的人拿到的文件表头是一串 `export.column.xxx`
    （`app/admin/tests/api_v1/test_export.py` 的全局版守着同一件事，这里盯材料这一份）
    """
    from backend.plugin.materials.dataio import MATERIAL_EXPORT

    keys = {MATERIAL_EXPORT.label, *MATERIAL_EXPORT.filter_labels.values()}
    keys.update(column.label for column in MATERIAL_EXPORT.columns)

    for name in ('zh-CN.yml', 'en-US.yml'):
        locale = yaml.safe_load((LOCALE_DIR / name).read_text(encoding='utf-8'))
        missing = []
        for key in sorted(keys):
            node: Any = locale
            for part in key.split('.'):
                node = node.get(part) if isinstance(node, dict) else None
            if not isinstance(node, str):
                missing.append(key)
        assert not missing, f'{name} 缺这些材料导出文案：{missing}'


def test_export_and_import_routes_require_their_permission_codes() -> None:
    """四个端点各自挂着 `pm:material:*` 的权限码 + `DependsRBAC`

    🔴 漏挂的表现是「按钮藏了但接口裸奔」（任何登录用户都能导全表）——
    而 `test_permission_codes.py` 只核对**出现过**的码，管不到「这条路由挂没挂」。
    """
    assert route_guards('/export') == (['pm:material:export'], True)
    for name in ('template', 'preview', 'commit'):
        assert route_guards(f'/import/{name}') == (['pm:material:import'], True), name
    # 列表 / 详情 / 增删改还在，别把顺序挪坏（`/{pk}` 只有一条一段的会吃掉后面的两段路径）
    assert route_guards('') == (['pm:material:list', 'pm:material:add', 'pm:material:del'], True)


def test_export_without_a_token_is_unauthorized(client: TestClient) -> None:
    res = client.post(EXPORT, json={})
    assert res.status_code == 401, res.text


def test_openapi_paths(client: TestClient) -> None:
    """扩展级插件路径多一层 `/sys`；`/import/*` 与 `/export` 都在 `GET /{pk}` 之前声明"""
    from backend.main import app

    paths = app.openapi()['paths']
    for suffix in ('', '/{pk}', '/export', '/import/template', '/import/preview', '/import/commit'):
        assert f'/api/v1/sys/materials{suffix}' in paths, suffix
    assert '/api/v1/materials' not in paths


def test_material_export_definition_shape() -> None:
    """定义本身：资源键 / 权限码 / 幂等键 / 三种模式 / 源表 sheet 名"""
    from backend.common.dataio.exporting import get_export
    from backend.common.dataio.importing import get_import

    spec = get_export('pm.material')
    assert spec is not None and spec.perm == 'pm:material:export'
    assert spec.id_column is not None

    import_spec = get_import('pm.material')
    assert import_spec is not None
    assert import_spec.sheet_names == ('Material',)
    assert set(import_spec.modes) == {'create', 'upsert', 'update'}
    assert import_spec.key_of({'source_id': 7}) == 'source:7'
    assert import_spec.key_of({'source_id': None}) is None
