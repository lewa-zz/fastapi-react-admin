"""WIR 台账的导入 / 导出定义。

源文件 `WIR Ledger_toDB.xlsx` 有两张表：`WIR`（289 行记录）和 `type`（36 个类型，
`WIR.type_id` 指向 `type.id`）。所以这里登记两个资源：

1. **WIR 类型**（`wir.type`）—— 读 `type` 表。源 `id` 原样保留：记录表的
   `type_id` 是这些 1..36 的数字，不保留的话导入完成之后对不上。
2. **WIR 记录**（`wir.record`）—— 读 `WIR` 表。`type_id` 按「库里的类型 ID 或
   类型中英文名」解析；`ID` 列进 `wir_record.source_id`，当幂等键 —— 289 行里
   243 行没有 TML 号，没有别的业务键能认出「同一行」。

导入顺序：**先类型、后记录**。记录 import 的 `validate` 会明确报「类型不存在」，
不会静默把 `type_id` 写成 NULL。

导出（`WIR_RECORD_EXPORT`）只导记录这张表，列就是 `WIR_RECORD_IMPORT` 认得的那一套
（外加 `id` / 创建 / 更新时间）—— 导出的文件改完能原样导回去。
"""

from collections.abc import Mapping
from typing import Any

from pydantic import ConfigDict, Field, ValidationError
from sqlalchemy import Select, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.admin.service.import_service import pydantic_errors
from backend.common.dataio.exporting import ExportColumn, ExportSpec, register_export
from backend.common.dataio.importing import (
    CommitOutcome,
    ImportColumn,
    ImportContext,
    ImportRow,
    ImportSpec,
    register_import,
)
from backend.common.exception import errors
from backend.common.i18n import t
from backend.common.log import log
from backend.common.schema import SchemaBase
from backend.plugin.wir.crud.crud_wir import wir_record_dao, wir_type_dao
from backend.plugin.wir.model.wir import WirRecord, WirType
from backend.plugin.wir.schema.wir import (
    CreateWirRecordParam,
    CreateWirTypeParam,
    UpdateWirRecordParam,
    UpdateWirTypeParam,
)
from backend.utils.serializers import select_columns_serialize

#: 一次 `IN (...)` 最多放多少个参数 —— SQL Server 一句最多 2100 个
_CHUNK = 1000

_RECORD_FIELDS = (
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
)


def _chunks(values: set[Any]) -> list[list[Any]]:
    ordered = sorted(values, key=str)
    return [ordered[start : start + _CHUNK] for start in range(0, len(ordered), _CHUNK)]


def _fields(values: Mapping[str, Any], current: Any) -> dict[str, Any]:
    """更新时空白单元格表示保持原值（同部门 / 字典导入）。新建时空白就是空。"""
    out: dict[str, Any] = {}
    for key in _RECORD_FIELDS:
        value = values.get(key)
        if value is None and current is not None:
            value = getattr(current, key)
        out[key] = value
    return out


# ═══════════════════════════════ 导出 ═══════════════════════════════


class WirRecordExportFilters(SchemaBase):
    """和 `GET /sys/wir` 的查询参数同名同义（`dc` / `discipline` / `doc_status` / `type_id` / `search`）。

    🔴 `extra='forbid'`：不认识的参数**报错**。忽略的话前端拼错一个参数名，那个条件就静默消失，
    导出的是全表而用户以为是筛过的那批（同 `plugin/materials/dataio.py` 的 `MaterialExportFilters`）
    """

    model_config = ConfigDict(extra='forbid')

    dc: str | None = Field(None, description='所属 DC')
    discipline: str | None = Field(None, description='专业')
    doc_status: str | None = Field(None, description='批复状态')
    # 前端筛选值走 URL，是字符串；pydantic 的宽松模式会把 `'3'` 收成 `3`（类型 ID 只有 1..36）
    type_id: int | None = Field(None, description='类型 ID')
    search: str | None = Field(None, description='搜索（描述 / 别称 / 编号）')


async def _record_select(f: WirRecordExportFilters, _user: Any) -> Select:
    """复用列表接口那个 DAO 查询 —— 数据范围（虽已豁免）/ 排序都在它里面，不另写裸 select"""
    return await wir_record_dao.get_select(
        dc=f.dc, discipline=f.discipline, doc_status=f.doc_status, type_id=f.type_id, search=f.search
    )


async def _columns_only(_db: AsyncSession, rows: Any) -> list[dict[str, Any]]:  # ruff: ignore[unused-async]
    """单表查询的行：`Row(WirRecord,)` → 列字典（`shape` 的签名是异步的）"""
    return [select_columns_serialize(row[0]) for row in rows]


WIR_RECORD_EXPORT = register_export(
    ExportSpec(
        resource='wir.record',
        label='export.resource.wir_record',
        perm='wir:export',
        columns=(
            ExportColumn('id', 'export.column.id', kind='id', width=22),
            # 源 Excel 的 `ID`：导出的表改完能原样导回去（它就是记录导入的幂等键）
            ExportColumn('source_id', 'export.column.wir_source_id', kind='int', width=10),
            ExportColumn('from_party', 'export.column.wir_from_party', width=12),
            ExportColumn('tml_no', 'export.column.wir_tml_no', width=30),
            ExportColumn('pmweb_no', 'export.column.wir_pmweb_no', width=44),
            ExportColumn('doc_type', 'export.column.wir_doc_type', width=12),
            ExportColumn('discipline', 'export.column.wir_discipline', width=12),
            ExportColumn('description', 'export.column.wir_description', width=50),
            ExportColumn('drt_submitted', 'export.column.wir_drt_submitted', kind='datetime', width=18),
            ExportColumn('pmx_submitted', 'export.column.wir_pmx_submitted', kind='datetime', width=18),
            ExportColumn('cb_inspection', 'export.column.wir_cb_inspection', kind='datetime', width=18),
            ExportColumn('doc_status', 'export.column.wir_doc_status', width=20),
            ExportColumn('comment', 'export.column.wir_comment', width=50),
            ExportColumn('another_desc', 'export.column.wir_another_desc', width=40),
            ExportColumn('dc', 'export.column.wir_dc', width=14),
            ExportColumn('filepath', 'export.column.wir_filepath', width=50),
            ExportColumn('type_id', 'export.column.wir_type', kind='int', width=20),
            ExportColumn('created_time', 'export.column.created_time', kind='datetime', width=20),
            ExportColumn('updated_time', 'export.column.updated_time', kind='datetime', width=20),
        ),
        filters=WirRecordExportFilters,
        # 🔴 表头直接复用 `export.column.wir_*`（导入那套），不另造一份同义的 `export.filter.*`：
        # 两个语言包里已经逐字译好了，再加一遍就是两份会各自漂移的文案
        filter_labels={
            'dc': 'export.column.wir_dc',
            'discipline': 'export.column.wir_discipline',
            'doc_status': 'export.column.wir_doc_status',
            'type_id': 'export.column.wir_type',
            'search': 'export.filter.search',
        },
        select=_record_select,
        id_column=WirRecord.id,
        shape=_columns_only,
    )
)


# ═══════════════════════════════ WIR 类型 ═══════════════════════════════


def _type_key(values: Mapping[str, Any]) -> str | None:
    type_cn = values.get('type_cn')
    return str(type_cn).strip() if type_cn else None


async def _type_validate(db: AsyncSession, rows: list[ImportRow], mode: str, _ctx: ImportContext) -> None:
    # 36 行，逐个查库足够；批量反而要处理「名字 / 源 ID 两个维度」
    for row in rows:
        values = row.values
        if not values.get('type_cn') or not values.get('type_en'):
            continue
        source_id = values.get('source_id')
        by_name = await wir_type_dao.get_by_name(db, values['type_cn'])
        by_id = await wir_type_dao.get(db, source_id) if source_id is not None else None
        if by_id is not None and by_name is not None and by_id.id != by_name.id:
            row.errors.append(t('error.wir.type_source_id_conflict', source_id=source_id, type_cn=by_id.type_cn))
            continue
        current = by_name or by_id
        if current is not None and mode == 'create':
            row.errors.append(t('error.import.key_exists', key=values['type_cn']))
            continue
        if current is None and mode == 'update':
            row.errors.append(t('error.import.key_not_found', key=values['type_cn']))
            continue
        payload = {
            'type_cn': values['type_cn'],
            'type_en': values['type_en'],
        }
        try:
            param = (CreateWirTypeParam if current is None else UpdateWirTypeParam)(**payload)
        except ValidationError as e:
            row.errors.extend(pydantic_errors(WIR_TYPE_IMPORT, e))
            continue
        row.action = 'create' if current is None else 'update'
        row.target_id = current.id if current is not None else None
        row.payload = {**param.model_dump(mode='json'), 'source_id': source_id}


async def _type_commit(db: AsyncSession, rows: list[ImportRow], _ctx: ImportContext) -> CommitOutcome:
    created: list[str] = []
    updated: list[str] = []
    failed: dict[int, str] = {}
    for row in rows:
        key = str(row.values['type_cn'])
        try:
            async with db.begin_nested():
                payload = dict(row.payload or {})
                source_id = payload.pop('source_id', None)
                if row.action == 'create':
                    obj = CreateWirTypeParam(**payload)
                    ins = WirType(**obj.model_dump())
                    # `id` 是 `init=False`，只能建好再赋；源 ID 1..36 不会和雪花撞
                    if source_id is not None:
                        ins.id = source_id
                    db.add(ins)
                    await db.flush()
                    created.append(key)
                else:
                    obj = UpdateWirTypeParam(**payload)
                    await wir_type_dao.update(db, row.target_id, obj)
                    updated.append(key)
        except errors.BaseExceptionError as e:
            failed[row.row_no] = e.msg
        except (SQLAlchemyError, ValidationError):
            log.exception(f'导入 WIR 类型 {key} 失败')
            failed[row.row_no] = t('error.import.row_unexpected')
    return CommitOutcome(created=created, updated=updated, failed=failed)


WIR_TYPE_IMPORT = register_import(
    ImportSpec(
        resource='wir.type',
        label='export.resource.wir_type',
        # 业务文件里叫 `type`；下载模板填完的文件只有一张 `数据`，回落第一张
        sheet_names=('type',),
        columns=(
            ImportColumn(
                'source_id',
                'export.column.wir_source_id',
                kind='int',
                aliases=('ID',),
                note='import.note.wir_type_source_id',
                width=10,
            ),
            ImportColumn('type_cn', 'export.column.wir_type_cn', required=True, width=30),
            ImportColumn('type_en', 'export.column.wir_type_en', required=True, width=42),
        ),
        key_of=_type_key,
        validate=_type_validate,
        commit=_type_commit,
        modes=('create', 'upsert'),
        notes=('import.note.wir_type_first', 'import.note.wir_type_source_id'),
    )
)


# ═══════════════════════════════ WIR 记录 ═══════════════════════════════


def _record_key(values: Mapping[str, Any]) -> str | None:
    source_id = values.get('source_id')
    if source_id is not None:
        return f'source:{source_id}'
    tml_no = values.get('tml_no')
    return f'tml:{tml_no}' if tml_no else None


async def _load_types(db: AsyncSession) -> tuple[dict[int, WirType], dict[str, WirType], dict[str, WirType]]:
    rows = (await db.scalars(select(WirType).where(WirType.deleted == 0))).all()
    return (
        {row.id: row for row in rows},
        {row.type_cn.casefold(): row for row in rows},
        {row.type_en.casefold(): row for row in rows},
    )


async def _load_existing(db: AsyncSession, rows: list[ImportRow]) -> tuple[dict[int, WirRecord], dict[str, WirRecord]]:
    by_source: dict[int, WirRecord] = {}
    source_ids = {row.values['source_id'] for row in rows if row.values.get('source_id') is not None}
    for chunk in _chunks(source_ids):
        for item in (
            await db.scalars(select(WirRecord).where(WirRecord.source_id.in_(chunk), WirRecord.deleted == 0))
        ).all():
            by_source[item.source_id] = item

    by_tml: dict[str, WirRecord] = {}
    tml_nos = {row.values['tml_no'] for row in rows if row.values.get('tml_no')}
    for chunk in _chunks(tml_nos):
        for item in (
            await db.scalars(select(WirRecord).where(WirRecord.tml_no.in_(chunk), WirRecord.deleted == 0))
        ).all():
            by_tml[item.tml_no] = item
    return by_source, by_tml


def _resolve_type(
    raw: Any, by_id: dict[int, WirType], by_cn: dict[str, WirType], by_en: dict[str, WirType]
) -> WirType | None:
    if raw is None:
        return None
    text = str(raw).strip()
    if not text:
        return None
    if text.isdigit():
        found = by_id.get(int(text))
        if found is not None:
            return found
    return by_cn.get(text.casefold()) or by_en.get(text.casefold())


async def _record_validate(db: AsyncSession, rows: list[ImportRow], mode: str, _ctx: ImportContext) -> None:
    by_id, by_cn, by_en = await _load_types(db)
    by_source, by_tml = await _load_existing(db, rows)

    for row in rows:
        values = row.values
        source_id = values.get('source_id')
        tml_no = values.get('tml_no')

        # 类型必须已经在库里：`type_id` 是文件里的 1..36 或用户填的中英文名
        type_value = values.get('type_id')
        wir_type = _resolve_type(type_value, by_id, by_cn, by_en)
        if type_value not in (None, '') and wir_type is None:
            row.errors.append(t('error.wir.import_type_unknown', value=type_value))
            continue

        current = by_source.get(source_id) if source_id is not None else (by_tml.get(tml_no) if tml_no else None)
        if current is not None and mode == 'create':
            row.errors.append(t('error.import.key_exists', key=_record_key(values) or ''))
            continue
        if current is None and mode == 'update':
            row.errors.append(t('error.import.key_not_found', key=_record_key(values) or ''))
            continue
        # TML 号是库上的唯一键：文件里这一行和库里另一行撞了要说清楚，不能等提交撞约束
        if tml_no:
            same_tml = by_tml.get(tml_no)
            if same_tml is not None and (current is None or same_tml.id != current.id):
                row.errors.append(t('error.wir.tml_no_exists', tml_no=tml_no))
                continue
        if current is None and tml_no is None and source_id is None:
            row.errors.append(t('error.wir.import_row_key_missing'))
            continue

        fields = _fields(values, current)
        if wir_type is not None:
            fields['type_id'] = wir_type.id
        try:
            param = (CreateWirRecordParam if current is None else UpdateWirRecordParam)(**fields)
        except ValidationError as e:
            row.errors.extend(pydantic_errors(WIR_RECORD_IMPORT, e))
            continue
        row.action = 'create' if current is None else 'update'
        row.target_id = current.id if current is not None else None
        row.payload = {**param.model_dump(mode='json'), 'source_id': source_id}


async def _record_commit(db: AsyncSession, rows: list[ImportRow], _ctx: ImportContext) -> CommitOutcome:
    created: list[str] = []
    updated: list[str] = []
    failed: dict[int, str] = {}
    for row in rows:
        key = _record_key(row.values) or f'row:{row.row_no}'
        try:
            async with db.begin_nested():
                payload = dict(row.payload or {})
                source_id = payload.pop('source_id', None)
                if row.action == 'create':
                    obj = CreateWirRecordParam(**payload)
                    ins = WirRecord(**obj.model_dump())
                    if source_id is not None:
                        ins.source_id = source_id
                    db.add(ins)
                    await db.flush()
                    created.append(key)
                else:
                    obj = UpdateWirRecordParam(**payload)
                    data = obj.model_dump(exclude_unset=True)
                    if source_id is not None:
                        data['source_id'] = source_id
                    await wir_record_dao.update_model_by_column(db, data, id=row.target_id, deleted=0)
                    updated.append(key)
        except errors.BaseExceptionError as e:
            failed[row.row_no] = e.msg
        except (SQLAlchemyError, ValidationError):
            log.exception(f'导入 WIR 记录 {key} 失败')
            failed[row.row_no] = t('error.import.row_unexpected')
    return CommitOutcome(created=created, updated=updated, failed=failed)


WIR_RECORD_IMPORT = register_import(
    ImportSpec(
        resource='wir.record',
        label='export.resource.wir_record',
        sheet_names=('WIR',),
        columns=(
            ImportColumn(
                'source_id',
                'export.column.wir_source_id',
                kind='int',
                aliases=('ID',),
                note='import.note.wir_record_source_id',
                width=10,
            ),
            ImportColumn('from_party', 'export.column.wir_from_party', aliases=('From',), width=12),
            ImportColumn('tml_no', 'export.column.wir_tml_no', aliases=('TML_No',), width=30),
            ImportColumn('pmweb_no', 'export.column.wir_pmweb_no', aliases=('PMWeb_No',), width=44),
            ImportColumn('doc_type', 'export.column.wir_doc_type', aliases=('Document_type',), width=12),
            ImportColumn('discipline', 'export.column.wir_discipline', aliases=('Disciplin',), width=12),
            ImportColumn('description', 'export.column.wir_description', aliases=('Description',), width=50),
            ImportColumn('drt_submitted', 'export.column.wir_drt_submitted', aliases=('DRT_SUBMITTED',), width=18),
            ImportColumn('pmx_submitted', 'export.column.wir_pmx_submitted', aliases=('PMX_SUBMITTED',), width=18),
            ImportColumn('cb_inspection', 'export.column.wir_cb_inspection', aliases=('CB_INSPECTION',), width=18),
            ImportColumn('doc_status', 'export.column.wir_doc_status', aliases=('Document_Status',), width=20),
            ImportColumn('comment', 'export.column.wir_comment', aliases=('COMMENT',), width=50),
            ImportColumn('another_desc', 'export.column.wir_another_desc', aliases=('another_desc',), width=40),
            ImportColumn('dc', 'export.column.wir_dc', aliases=('dc',), width=14),
            ImportColumn('filepath', 'export.column.wir_filepath', aliases=('filepath',), width=50),
            ImportColumn(
                'type_id',
                'export.column.wir_type',
                aliases=('type_id',),
                note='import.note.wir_record_type',
                width=20,
            ),
        ),
        key_of=_record_key,
        validate=_record_validate,
        commit=_record_commit,
        modes=('create', 'upsert'),
        notes=('import.note.wir_record_type', 'import.note.update_keeps_blank'),
    )
)
