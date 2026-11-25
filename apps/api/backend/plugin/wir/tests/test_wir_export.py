"""WIR 台账导出（`POST /sys/wir/export`）。

照 `plugin/materials/tests/test_pm_material_import.py` 的导出那一段抄，盯的是
**「文件生成了、内容是错的」**那一类 —— 它们都不报错：

- **筛选参数静默丢了**：导出全表，而用户以为是列表上筛过的那批
- **筛选值类型对不上**：前端把 `type_id` 按字符串传（URL 里只有字符串），
  模型收不下就会 400，或者收成了 `0` 而筛出空
- **列名 / 筛选名没有译文**：那门语言的人拿到的表头是一串 `export.column.wir_xxx`

⚠️ 接口的删除是逻辑删除，`source_id` / `tml_no` 的唯一性还占着 —— 收尾要硬删
（同 `plugin/wir/tests/test_wir_import.py` 的 `purge()`）。
"""

import asyncio
import io

from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest
import yaml

from openpyxl import load_workbook
from sqlalchemy import text
from starlette.testclient import TestClient

from backend.core.path_conf import LOCALE_DIR
from backend.database.db import create_database_async_engine, create_database_async_session, get_database_url

WIR = '/sys/wir'
WIR_TYPES = '/sys/wir/types'
EXPORT = '/sys/wir/export'
EXPORTS = '/sys/exports'

DC1 = 'DC1-Fitout'
DC2 = 'DC2-Fitout'


def purge() -> None:
    """硬删这两张表：接口的删除是逻辑删除，`tml_no` 的唯一性还占着。"""

    async def _run() -> None:
        engine = create_database_async_engine(get_database_url(unittest=True))
        session_maker = create_database_async_session(engine)
        try:
            async with session_maker.begin() as session:
                await session.execute(text('DELETE FROM wir_record'))
                await session.execute(text('DELETE FROM wir_type'))
        finally:
            await engine.dispose()

    asyncio.run(_run())


def purge_jobs() -> None:
    """导出记录也要清：并发上限按「排队 / 生成中」的条数算，残留会让下一条撞上限"""

    async def _run() -> None:
        engine = create_database_async_engine(get_database_url(unittest=True))
        session_maker = create_database_async_session(engine)
        try:
            async with session_maker.begin() as session:
                await session.execute(text('DELETE FROM sys_export_job'))
        finally:
            await engine.dispose()

    asyncio.run(_run())


@pytest.fixture(autouse=True)
def _clean() -> Iterator[None]:
    purge()
    purge_jobs()
    yield
    purge()
    purge_jobs()


@pytest.fixture(autouse=True)
def _isolated_upload_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """导出文件落在内置本地存储的私有树上，顶到 tmp（接缝同 `test_export.py` / `test_file.py`）"""
    from backend.utils import file_ops

    upload_dir = tmp_path / 'upload'
    public_dir = tmp_path / 'upload-public'
    upload_dir.mkdir()
    public_dir.mkdir()
    monkeypatch.setattr(file_ops, 'UPLOAD_DIR', upload_dir)
    monkeypatch.setattr(file_ops, 'PUBLIC_UPLOAD_DIR', public_dir)
    return upload_dir


def create_record(client: TestClient, headers: dict[str, str], **overrides: Any) -> dict:
    payload = {
        'from_party': 'DRT',
        'doc_type': 'WIR',
        'discipline': 'BMS',
        'description': 'CABLE TRAY INSTALLATION',
        'dc': DC1,
        'doc_status': 'Approved',
        **overrides,
    }
    res = client.post(WIR, headers=headers, json=payload)
    assert res.status_code == 200, res.text
    return res.json()['data']


def create_type(client: TestClient, headers: dict[str, str], type_cn: str, type_en: str) -> dict:
    res = client.post(WIR_TYPES, headers=headers, json={'type_cn': type_cn, 'type_en': type_en})
    assert res.status_code == 200, res.text
    return res.json()['data']


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


def exported_ids(client: TestClient, headers: dict[str, str], filters: dict[str, Any]) -> set[str]:
    """按筛选导一次，取文件里 ID 那一列"""
    body = export(client, headers, {'filters': filters})
    assert body['code'] == 200, body
    job = body['data']
    assert job['status'] == 2, job  # 小批量当场生成完
    header, rows = sheet_rows(download(client, headers, job['id']))
    position = header.index('ID')
    ids = {str(row[position]) for row in rows}
    assert len(rows) == job['total'] == job['row_count'], job
    return ids


def route_guards(path: str) -> tuple[list[str], bool]:
    """这条路由上挂了哪些 `RequestPermission` 码、有没有 `DependsRBAC`

    直接看**插件自己的 router**：`app.routes` 里只有十几条（API 挂在 Mount 下面），
    遍历它一个 WIR 路径都找不到 —— 那种「什么都没扫到」会让断言假绿。
    """
    from backend.common.security.permission import RequestPermission
    from backend.plugin.wir.api.v1.sys.wir import router

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


# ═══════════════════════════════ 按筛选导出 ═══════════════════════════════


def test_export_writes_the_filtered_rows(client: TestClient, token_headers: dict[str, str]) -> None:
    """导出的是列表接口筛出来的那批（筛选参数同名同义）"""
    a = create_record(client, token_headers, description='CABLE TRAY A', tml_no='TML-A')
    b = create_record(client, token_headers, description='CABLE TRAY B', discipline='SEC')
    c = create_record(client, token_headers, description='CABLE TRAY C', dc=DC2, tml_no='TML-C')

    listed = client.get(WIR, headers=token_headers, params={'dc': DC1}).json()['data']
    assert listed['total'] == 2  # 先断言「列表上真的有两条」，否则下面的集合断言分不出对错

    assert exported_ids(client, token_headers, {'dc': DC1}) == {a['id'], b['id']}
    # 不传筛选 = 全部
    assert exported_ids(client, token_headers, {}) == {a['id'], b['id'], c['id']}
    # 换一个 DC：证明筛的是条件，不是「刚好只有这两条」
    assert exported_ids(client, token_headers, {'dc': DC2}) == {c['id']}


def test_export_filters_by_discipline_and_search(client: TestClient, token_headers: dict[str, str]) -> None:
    """`discipline` 全等、`search` 模糊（描述 / 别称 / TML / PMWeb 四列）"""
    a = create_record(client, token_headers, description='CABLE TRAY A', tml_no='TML-A')
    b = create_record(client, token_headers, description='DUCT BANK B', discipline='ELV')
    create_record(client, token_headers, description='CABLE TRAY C', discipline='ELV', dc=DC2)

    assert exported_ids(client, token_headers, {'discipline': 'BMS'}) == {a['id']}
    assert exported_ids(client, token_headers, {'discipline': 'ELV', 'dc': DC1}) == {b['id']}
    # 搜 TML 号（search 在 DAO 里就是这四个列上 ilike）
    assert exported_ids(client, token_headers, {'search': 'TML-A'}) == {a['id']}


def test_export_filters_by_type_id_sent_as_a_string(client: TestClient, token_headers: dict[str, str]) -> None:
    """🔴 前端把筛选值按**字符串**传（URL 里只有字符串）：`type_id` 收不下就是 400，收成 0 就筛出空"""
    tray = create_type(client, token_headers, 'BMS 桥架安装', 'BMS Cable Tray Installation')
    duct = create_type(client, token_headers, 'ELV 线管安装', 'ELV Conduit Installation')
    a = create_record(client, token_headers, type_id=int(tray['id']), description='TRAY')
    b = create_record(client, token_headers, type_id=int(duct['id']), description='DUCT')

    assert exported_ids(client, token_headers, {'type_id': str(tray['id'])}) == {a['id']}
    assert exported_ids(client, token_headers, {'type_id': str(duct['id'])}) == {b['id']}


def test_export_rejects_an_unknown_filter(client: TestClient, token_headers: dict[str, str]) -> None:
    """拼错的筛选参数被忽略 = 导出全表，而用户以为是筛过的（`extra='forbid'`）"""
    create_record(client, token_headers)
    body = export(client, token_headers, {'filters': {'dcc': DC1}})
    assert body['code'] == 400, body
    assert 'dcc' in body['msg'], body


def test_export_file_starts_with_the_wir_columns(client: TestClient, token_headers: dict[str, str]) -> None:
    """表头是资源定义的全量列（不是列表上看得见的那几列），且 ID 按文本写"""
    record = create_record(client, token_headers, description='CABLE TRAY A')
    body = export(client, token_headers, {'columns': ['id', 'description', 'dc']})
    assert body['code'] == 200, body
    job = body['data']
    header, rows = sheet_rows(download(client, token_headers, job['id']))
    assert header == ['ID', '检查内容', '所属 DC'], header
    assert rows[0] == [record['id'], 'CABLE TRAY A', DC1]


# ═══════════════════════════════ 权限 / 契约 ═══════════════════════════════


def test_export_route_requires_its_permission_code() -> None:
    """导出这条路由挂着 `wir:export` + `DependsRBAC`

    🔴 漏挂的表现是「按钮藏了但接口裸奔」（任何登录用户都能导全表）——
    而 `test_permission_codes.py` 只核对**出现过**的码，管不到「这条路由挂没挂」。
    """
    assert route_guards('/export') == (['wir:export'], True)


def test_export_without_a_token_is_unauthorized(client: TestClient) -> None:
    res = client.post(EXPORT, json={})
    assert res.status_code == 401, res.text


def test_openapi_paths(client: TestClient) -> None:
    """扩展级插件路径多一层 `/sys`；`/export` 声明在 `GET /{pk}` 之前（否则被 pk 吞掉）"""
    from backend.main import app

    paths = app.openapi()['paths']
    for suffix in ('', '/{pk}', '/export', '/import/template', '/import/preview', '/import/commit'):
        assert f'/api/v1/sys/wir{suffix}' in paths, suffix
    assert '/api/v1/wir' not in paths


def test_export_definition_shape() -> None:
    """定义本身：资源键 / 权限码 / 筛选字段 / 列 key 与导入那一套对齐"""
    from backend.common.dataio.exporting import get_export
    from backend.plugin.wir.dataio import WIR_RECORD_IMPORT, WirRecordExportFilters

    spec = get_export('wir.record')
    assert spec is not None
    assert spec.label == 'export.resource.wir_record'
    assert spec.perm == 'wir:export'
    assert spec.id_column is not None
    assert set(spec.column_keys()) == {
        'id',
        'source_id',
        'from_party',
        'tml_no',
        'pmweb_no',
        'doc_type',
        'discipline',
        'description',
        'drt_submitted',
        'pmx_submitted',
        'cb_inspection',
        'doc_status',
        'comment',
        'another_desc',
        'dc',
        'filepath',
        'type_id',
        'created_time',
        'updated_time',
    }
    # 导出的列 key ⊇ 导入认的字段（导入还有个 `source_id`，也在导出里）
    assert {column.key for column in WIR_RECORD_IMPORT.columns} <= set(spec.column_keys())

    # 筛选字段和 `GET /sys/wir` 的查询参数同名
    assert set(WirRecordExportFilters.model_fields) == {'dc', 'discipline', 'doc_status', 'type_id', 'search'}
    assert set(spec.filter_labels) == set(WirRecordExportFilters.model_fields)

    # 不认识的参数要报错，不能忽略
    with pytest.raises(Exception):
        WirRecordExportFilters.model_validate({'nope': 1})


def test_export_columns_are_all_translated() -> None:
    """列名 / 筛选名 / 资源名都是运行时拼的键（`t(column.label)`），`test_i18n.py` 的正则扫不到

    缺键的表现：那门语言的人拿到的文件表头是一串 `export.column.wir_xxx`
    （`app/admin/tests/api_v1/test_export.py` 的全局版守着同一件事，这里盯 WIR 这份）
    """
    from backend.plugin.wir.dataio import WIR_RECORD_EXPORT

    keys = {WIR_RECORD_EXPORT.label, *WIR_RECORD_EXPORT.filter_labels.values()}
    keys.update(column.label for column in WIR_RECORD_EXPORT.columns)

    for name in ('zh-CN.yml', 'en-US.yml'):
        locale = yaml.safe_load((LOCALE_DIR / name).read_text(encoding='utf-8'))
        missing = []
        for key in sorted(keys):
            node: Any = locale
            for part in key.split('.'):
                node = node.get(part) if isinstance(node, dict) else None
            if not isinstance(node, str):
                missing.append(key)
        assert not missing, f'{name} 缺这些 WIR 导出文案：{missing}'


def test_export_menu_is_seeded_in_every_dialect() -> None:
    """三个方言的雪花种子里都要有这条按钮 —— 少一份的表现是「那个库上非超管永远 403」

    `test_permission_codes.py` 只要求「后端挂的码在**某个**种子文件里出现过」，
    不要求每个方言都有。
    """
    from backend.core.path_conf import BASE_PATH

    for dialect in ('mysql', 'postgresql', 'sqlserver'):
        init = BASE_PATH / 'plugin' / 'wir' / 'sql' / dialect / 'init_snowflake.sql'
        destroy = BASE_PATH / 'plugin' / 'wir' / 'sql' / dialect / 'destroy_snowflake.sql'
        assert "'ExportWirRecord'" in init.read_text(encoding='utf-8'), f'{dialect} 的 init 里没有这条按钮'
        # 卸载不删它 = 父级菜单被删之后它变成孤儿，被 `traversal_to_tree` 提到侧边栏根上
        assert "'ExportWirRecord'" in destroy.read_text(encoding='utf-8'), f'{dialect} 的 destroy 里没删它'
