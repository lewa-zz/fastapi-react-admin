"""WIR 台账 Excel 导入：两张表的顺序、类型 ID 的保留、按 source_id 幂等。

源文件 `WIR Ledger_toDB.xlsx` 的结构不是「一张表」：`WIR` 表 289 行记录，
`type` 表 36 个类型，记录的 `type_id` 指向类型表的 `id`。所以这里盯三件
「导进去了但不对」的事：

- 类型表在第二张表上，不显式选表就会读成记录表
- 类型不保留源 ID，记录表的 `type_id` 全部对不上
- 没有 TML 号的记录没有业务键，重导一次就多 289 行
"""

import asyncio
import datetime as dt
import io

from collections.abc import Iterator

import openpyxl
import pytest

from openpyxl import Workbook
from sqlalchemy import text
from starlette.testclient import TestClient

from backend.database.db import create_database_async_engine, create_database_async_session, get_database_url

WIR_TYPES = '/sys/wir/types'
WIR_TYPE_IMPORT = '/sys/wir/types/import'
WIR_RECORDS = '/sys/wir'
WIR_IMPORT = '/sys/wir/import'

#: 记录导入的接口前缀（下面几个测试共用）
WIR_RECORD_IMPORT = WIR_IMPORT

XLSX = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'

#: 原文件的表头（不是我们起的 key）：证明别名能认出来
RECORD_HEADER = [
    'ID',
    'From',
    'TML_No',
    'PMWeb_No',
    'Document_type',
    'Disciplin',
    'Description',
    'DRT_SUBMITTED',
    'PMX_SUBMITTED',
    'CB_INSPECTION',
    'Document_Status',
    'COMMENT',
    'another_desc',
    'dc',
    'filepath',
    'type_id',
]


def build_xlsx() -> bytes:
    """两张表：`type`（id / type_cn / type_en）在前，`WIR` 在后 —— 顺序和源文件相反也能选中。"""
    wb = Workbook()
    wb.remove(wb.active)

    type_ws = wb.create_sheet('type')
    type_ws.append(['id', 'type_cn', 'type_en'])
    type_ws.append([1, 'BMS 桥架安装', 'BMS Cable Tray Installation'])
    type_ws.append([2, 'ELV 桥架安装', 'ELV Cable Tray Installation'])

    ws = wb.create_sheet('WIR')
    ws.append(RECORD_HEADER)
    # 第一条用数字的 type ID；第二条用英文名 —— 两种写法都要能对上
    ws.append([
        1,
        'DRT',
        'TML-IMP-1',
        'PM-IMP-1',
        'WIR',
        'BMS',
        'CABLE TRAY INSTALLATION',
        dt.date(2026, 10, 4),
        None,
        None,
        'Approved',
        'ok',
        'BMS tray WIR',
        'DC1-Fitout',
        None,
        1,
    ])
    ws.append([
        2,
        'DRT',
        None,
        None,
        'WIR',
        'BMS',
        'CABLE TRAY INSTALLATION 2',
        None,
        None,
        None,
        None,
        None,
        'BMS tray WIR 2',
        'DC1-Fitout',
        None,
        'BMS Cable Tray Installation',
    ])

    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


def upload(client: TestClient, headers: dict[str, str], base: str, raw: bytes, mode: str = 'create') -> dict:
    res = client.post(
        f'{base}/preview?mode={mode}',
        headers=headers,
        files={'file': ('wir.xlsx', raw, XLSX)},
    )
    assert res.status_code == 200, res.text
    body = res.json()
    assert body['code'] == 200, body
    return body['data']


def commit(client: TestClient, headers: dict[str, str], base: str, token: str) -> dict:
    res = client.post(
        f'{base}/commit',
        headers=headers,
        json={'import_token': token, 'exclude_rows': [], 'atomic': False},
    )
    assert res.status_code == 200, res.text
    body = res.json()
    assert body['code'] == 200, body
    return body['data']


def purge() -> None:
    """硬删这两张表：接口的删除是逻辑删除，`source_id` / 类型还会占着唯一性。"""

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


@pytest.fixture(autouse=True)
def _clean_wir() -> Iterator[None]:
    purge()
    yield
    purge()


@pytest.fixture(scope='module')
def raw() -> bytes:
    return build_xlsx()


def test_type_import_reads_the_type_sheet_and_keeps_source_ids(
    client: TestClient, token_headers: dict[str, str], raw: bytes
) -> None:
    preview = upload(client, token_headers, WIR_TYPE_IMPORT, raw)
    assert preview['total'] == 2
    assert preview['valid'] == 2
    assert preview['ignored_headers'] == []
    assert [row['values']['type_cn'] for row in preview['rows']] == ['BMS 桥架安装', 'ELV 桥架安装']

    result = commit(client, token_headers, WIR_TYPE_IMPORT, preview['import_token'])
    assert result['committed'] is True
    assert len(result['created']) == 2

    types = client.get(WIR_TYPES, headers=token_headers).json()['data']
    assert {(item['id'], item['type_cn']) for item in types} == {
        ('1', 'BMS 桥架安装'),
        ('2', 'ELV 桥架安装'),
    }


def test_record_import_maps_type_id_and_is_idempotent(
    client: TestClient, token_headers: dict[str, str], raw: bytes
) -> None:
    types_preview = upload(client, token_headers, WIR_TYPE_IMPORT, raw)
    commit(client, token_headers, WIR_TYPE_IMPORT, types_preview['import_token'])

    preview = upload(client, token_headers, WIR_RECORD_IMPORT, raw)
    assert preview['total'] == 2
    assert preview['valid'] == 2
    # 两条都用「BMS 桥架安装」：一条填数字 1、一条填英文名
    assert {row['values']['type_id'] for row in preview['rows']} == {'1', 'BMS Cable Tray Installation'}

    result = commit(client, token_headers, WIR_RECORD_IMPORT, preview['import_token'])
    assert result['committed'] is True
    assert len(result['created']) == 2

    page = client.get(WIR_RECORDS, headers=token_headers).json()['data']
    assert page['total'] == 2
    rows = {item['id']: item for item in page['items']}
    assert {item['type_cn'] for item in rows.values()} == {'BMS 桥架安装'}
    assert {item['tml_no'] for item in rows.values()} == {'TML-IMP-1', None}

    # 再导一遍（upsert）：按 `source_id` 认回同一行，不是又建两条
    again = upload(client, token_headers, WIR_RECORD_IMPORT, raw, mode='upsert')
    assert again['to_update'] == 2
    assert again['to_create'] == 0
    result2 = commit(client, token_headers, WIR_RECORD_IMPORT, again['import_token'])
    assert result2['committed'] is True
    assert len(result2['updated']) == 2
    assert client.get(WIR_RECORDS, headers=token_headers).json()['data']['total'] == 2


def test_record_import_reports_an_unknown_type_instead_of_writing_null(
    client: TestClient, token_headers: dict[str, str], raw: bytes
) -> None:
    types_preview = upload(client, token_headers, WIR_TYPE_IMPORT, raw)
    commit(client, token_headers, WIR_TYPE_IMPORT, types_preview['import_token'])

    # 把文件里两条的 type_id 都换成不存在的 999：不能静默写成 NULL
    original = build_xlsx()
    wb = openpyxl.load_workbook(io.BytesIO(original))
    ws = wb['WIR']
    ws.cell(row=2, column=16).value = 999
    ws.cell(row=3, column=16).value = 999
    buf = io.BytesIO()
    wb.save(buf)

    preview = upload(client, token_headers, WIR_RECORD_IMPORT, buf.getvalue())
    assert preview['valid'] == 0
    assert preview['total'] == 2
    assert all(not row['ok'] and '类型' in row['errors'][0] for row in preview['rows'])
