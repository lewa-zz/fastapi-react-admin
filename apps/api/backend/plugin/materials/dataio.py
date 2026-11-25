"""PM 材料主数据的导入 / 导出定义。

取数调**列表接口那条** `pm_material_dao.get_select`（数据范围挂在 DAO 上，不另写裸 select），
筛选参数和 `GET /sys/materials` 的查询参数同名 —— 和 `plugin/notice/dataio.py` /
`plugin/wir/dataio.py` 同一套写法。

导入这一份的模板来自桌面 `材料表.xlsx`（sheet `Material`，100 条 + 1 行合计），
所以列名一律用 `aliases` 认**源表的原表头**，让「直接导材料表」和「下载模板填完再导」
共用同一份定义：

| Excel 表头 | 列 | 说明 |
|---|---|---|
| `id` | `source_id` | 导入幂等键（`(source_id, deleted)` 唯一），同一份表导两次不重复 |
| `type` | `kind` | Python 保留字，库列只能叫 `kind` |
| `mat_CN` / `mat_EN` | `name_cn` / `name_en` | |
| `amo` | `qty` | 合同数量 |
| `"\\tunit"` | `unit` | 源表第 10 列的表头带一个制表符（`plugin/materials/CLAUDE.md`），两种写法都认 |
| 金额五列 | 同名 | `Numeric(14, 4)`，读进来先转 `Decimal` 再过 schema |

🔴 **金额 / 数量的 `ImportColumn.kind` 只能是 `text`。** 框架的 `kind` 只有 `'text'` / `'int'`
两种（`common/dataio/importing.py`），没有 `'number'`：数字列的转换放在 `_to_decimals()`，
显式 `Decimal(str)` —— 中间过一手 `float` 会把 `0.0001` 变成 `0.0001` 之外的东西
（`Numeric(14,4)` 上差一分钱是真金白银）。

没有 `source_id` 的行（手工填的模板）只能**新增**：update 模式下认不出要改哪一条，
upsert 下按新增处理。
"""

from collections.abc import Mapping
from decimal import Decimal, InvalidOperation
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
from backend.plugin.materials.crud.crud_material import pm_material_dao
from backend.plugin.materials.model.material import PmMaterial
from backend.plugin.materials.schema.material import CreatePmMaterialParam, UpdatePmMaterialParam
from backend.utils.serializers import select_columns_serialize

#: 一次 `IN (...)` 最多放多少个参数 —— SQL Server 一句最多 2100 个（同 `plugin/wir/dataio.py`）
_CHUNK = 1000

#: 可导入的字段（`currency` / `active` 不在里面：模板里没有这两列，新建走 schema 默认值）
_MATERIAL_FIELDS = (
    'kind',
    'category',
    'name_cn',
    'name_en',
    'model',
    'spec',
    'brand',
    'qty',
    'unit',
    'price',
    'contract_price',
    'in_price',
    'out_price',
    'market_price',
    'memo',
    'source',
)

#: 金额 / 数量六列：`Numeric(14, 4)`，落库前必须显式转 `Decimal`
_NUMBER_COLUMNS = ('qty', 'price', 'contract_price', 'in_price', 'out_price', 'market_price')


# ═══════════════════════════════ 导出 ═══════════════════════════════


class MaterialExportFilters(SchemaBase):
    """和 `GET /sys/materials` 的查询参数同名同义。

    🔴 `extra='forbid'`：不认识的参数**报错**。忽略的话前端拼错一个参数名，那个条件就静默消失，
    导出的是全表而用户以为是筛过的那批（`app/admin/dataio.py: _Filters` /
    `plugin/notice/dataio.py` 同一个基类口径 —— 那个基类是 `app/admin` 私有的，
    插件这边各自声明一份）
    """

    model_config = ConfigDict(extra='forbid')

    kind: str | None = Field(None, description='类型')
    category: str | None = Field(None, description='类别')
    brand: str | None = Field(None, description='品牌')
    active: bool | None = Field(None, description='是否启用（不传=全部）')
    search: str | None = Field(None, description='搜索（中文名/英文名/型号/规格）')


async def _material_select(f: MaterialExportFilters, _user: Any) -> Select:
    """复用列表接口那个 DAO 查询 —— 数据范围 / 排序（SQL Server 的 OFFSET 要 ORDER BY）都在它里面"""
    return await pm_material_dao.get_select(
        kind=f.kind, category=f.category, brand=f.brand, active=f.active, search=f.search
    )


async def _columns_only(_db: AsyncSession, rows: Any) -> list[dict[str, Any]]:  # ruff: ignore[unused-async]
    """单表查询的行：`Row(PmMaterial,)` → 列字典（`shape` 的签名是异步的）"""
    return [select_columns_serialize(row[0]) for row in rows]


MATERIAL_EXPORT = register_export(
    ExportSpec(
        resource='pm.material',
        label='export.resource.material',
        perm='pm:material:export',
        columns=(
            ExportColumn('id', 'export.column.id', kind='id', width=22),
            # 源 Excel 的 `id`：导出的表改完能原样导回去（它就是导入的幂等键、别名 `id`）
            ExportColumn('source_id', 'export.column.source_id', kind='int', width=10),
            ExportColumn('kind', 'export.column.kind', width=22),
            ExportColumn('category', 'export.column.category', width=20),
            ExportColumn('name_cn', 'export.column.name_cn', width=34),
            ExportColumn('name_en', 'export.column.name_en', width=40),
            ExportColumn('model', 'export.column.model', width=22),
            ExportColumn('spec', 'export.column.spec', width=60),
            ExportColumn('brand', 'export.column.brand', width=16),
            ExportColumn('qty', 'export.column.qty', kind='number', width=10),
            ExportColumn('unit', 'export.column.unit', width=10),
            ExportColumn('price', 'export.column.price', kind='number', width=14),
            ExportColumn('contract_price', 'export.column.contract_price', kind='number', width=14),
            ExportColumn('in_price', 'export.column.in_price', kind='number', width=14),
            ExportColumn('out_price', 'export.column.out_price', kind='number', width=14),
            ExportColumn('market_price', 'export.column.market_price', kind='number', width=14),
            ExportColumn('memo', 'export.column.memo', width=20),
            ExportColumn('source', 'export.column.source', width=16),
            ExportColumn('currency', 'export.column.currency', width=8),
            ExportColumn('active', 'export.column.active', kind='bool', width=8),
            ExportColumn('created_time', 'export.column.created_time', kind='datetime', width=20),
            ExportColumn('updated_time', 'export.column.updated_time', kind='datetime', width=20),
        ),
        filters=MaterialExportFilters,
        filter_labels={
            'kind': 'export.column.kind',
            'category': 'export.column.category',
            'brand': 'export.column.brand',
            'active': 'export.column.active',
            'search': 'export.filter.search',
        },
        select=_material_select,
        id_column=PmMaterial.id,
        shape=_columns_only,
    )
)


# ═══════════════════════════════ 导入 ═══════════════════════════════


def _material_key(values: Mapping[str, Any]) -> str | None:
    """业务键：源表的 `id`。没有它就没有任何能认出「同一行」的东西，只能新增"""
    source_id = values.get('source_id')
    return f'source:{source_id}' if source_id is not None else None


def _chunks(values: set[Any]) -> list[list[Any]]:
    ordered = sorted(values, key=str)
    return [ordered[start : start + _CHUNK] for start in range(0, len(ordered), _CHUNK)]


async def _load_existing(db: AsyncSession, rows: list[ImportRow]) -> dict[int, PmMaterial]:
    """按 `source_id` 批量查已有行：一次 `IN` 分块 1000，不逐行往返"""
    by_source: dict[int, PmMaterial] = {}
    source_ids = {row.values['source_id'] for row in rows if row.values.get('source_id') is not None}
    for chunk in _chunks(source_ids):
        for item in (
            await db.scalars(select(PmMaterial).where(PmMaterial.source_id.in_(chunk), PmMaterial.deleted == 0))
        ).all():
            by_source[item.source_id] = item
    return by_source


def _fields(values: Mapping[str, Any], current: PmMaterial | None) -> dict[str, Any]:
    """一行要写成的字段。更新时**空白单元格表示保持原值**（不是清空）—— 只改一列的人不用把整行抄全"""
    out: dict[str, Any] = {}
    for key in _MATERIAL_FIELDS:
        value = values.get(key)
        if value is None and current is not None:
            value = getattr(current, key)
        out[key] = value
    return out


def _to_decimals(row: ImportRow, fields: dict[str, Any]) -> None:
    """金额 / 数量：`Decimal(str)` 显式转换。

    🔴 不要让它走 `float`：`Numeric(14, 4)` 上的差一分钱是真金白银（同 `plugin/materials/AGENTS.md`
    的「不要 `Mapped[float]`」）。公式格 / 超范围数字在解析层已经被拒了，这里只处理
    「填了非数字」这一种。
    """
    for key in _NUMBER_COLUMNS:
        raw = fields.get(key)
        if raw is None:
            continue
        # 文本格里常见千分位逗号（数字格不会走到这里：`excel_ops` 已经归一成 '1015.625'）
        text = str(raw).replace(',', '').replace('，', '').strip()
        if not text:
            fields[key] = None
            continue
        try:
            fields[key] = Decimal(text)
        except InvalidOperation:
            row.errors.append(
                t(
                    'error.pm.import_bad_number',
                    column=t(MATERIAL_IMPORT.column(key).label),
                    value=row.values.get(key),
                )
            )


async def _material_validate(db: AsyncSession, rows: list[ImportRow], mode: str, _ctx: ImportContext) -> None:
    """按 `source_id` 定新增还是更新；`create` 撞已存在 / `update` 找不到都报出来（不静默覆盖 / 静默丢弃）"""
    by_source = await _load_existing(db, rows)

    for row in rows:
        values = row.values
        source_id = values.get('source_id')
        current = by_source.get(source_id) if source_id is not None else None
        key = _material_key(values) or ''

        if current is None and mode == 'update' and source_id is None:
            # 没有幂等键的行认不出要改哪一条：说清楚，别让它静静地「更新了个寂寞」
            row.errors.append(t('error.pm.import_source_id_required'))
            continue
        if current is not None and mode == 'create':
            row.errors.append(t('error.import.key_exists', key=key))
            continue
        if current is None and mode == 'update':
            row.errors.append(t('error.import.key_not_found', key=key))
            continue

        fields = _fields(values, current)
        _to_decimals(row, fields)
        if row.errors:
            continue

        try:
            param = CreatePmMaterialParam(**fields) if current is None else UpdatePmMaterialParam(**fields)
        except ValidationError as e:
            row.errors.extend(pydantic_errors(MATERIAL_IMPORT, e))
            continue
        row.action = 'create' if current is None else 'update'
        row.target_id = current.id if current is not None else None
        # `mode='json'`：payload 要过一次 Redis，`Decimal` 在那里会变成 str（标度保住）。
        # 🔴 **只挑可导入的字段**：整份 dump 里带着 `currency` / `active`（Update 模型里是
        # `None`），原样传回去会被 `exclude_unset=True` 当成「显式设成 NULL」写进库 ——
        # 实测（PostgreSQL）：`null value in column "currency" violates not-null constraint`，
        # 而那一行在预览里是「能导入」的
        dump = param.model_dump(mode='json')
        row.payload = {**{key: dump[key] for key in _MATERIAL_FIELDS}, 'source_id': source_id}


async def _material_commit(db: AsyncSession, rows: list[ImportRow], _ctx: ImportContext) -> CommitOutcome:
    """一行一个保存点：一行写不进去不影响别的行（PostgreSQL 上一句失败整个事务就作废）"""
    created: list[str] = []
    updated: list[str] = []
    failed: dict[int, str] = {}

    for row in rows:
        key = _material_key(row.values) or f'row:{row.row_no}'
        try:
            async with db.begin_nested():
                payload = dict(row.payload or {})
                source_id = payload.pop('source_id', None)
                if row.action == 'create':
                    obj = CreatePmMaterialParam(**payload)
                    ins = PmMaterial(**obj.model_dump())
                    if source_id is not None:
                        ins.source_id = source_id
                    db.add(ins)
                    await db.flush()
                    created.append(key)
                else:
                    obj = UpdatePmMaterialParam(**payload)
                    data = obj.model_dump(exclude_unset=True)
                    if source_id is not None:
                        data['source_id'] = source_id
                    await pm_material_dao.update_model_by_column(db, data, id=row.target_id, deleted=0)
                    updated.append(key)
        except errors.BaseExceptionError as e:
            failed[row.row_no] = e.msg
        except (SQLAlchemyError, ValidationError):
            log.exception(f'导入材料 {key} 失败')
            failed[row.row_no] = t('error.import.row_unexpected')

    return CommitOutcome(created=created, updated=updated, failed=failed)


MATERIAL_IMPORT = register_import(
    ImportSpec(
        resource='pm.material',
        label='export.resource.material',
        # 源文件 `材料表.xlsx` 的 sheet 名；下载模板填完的文件只有一张「数据」，回落第一张
        sheet_names=('Material',),
        columns=(
            ImportColumn(
                'source_id',
                'export.column.source_id',
                kind='int',
                aliases=('id', 'ID'),
                note='import.note.material_source_id',
                width=10,
            ),
            ImportColumn('kind', 'export.column.kind', required=True, aliases=('type',), width=22),
            ImportColumn('category', 'export.column.category', required=True, aliases=('Category',), width=20),
            ImportColumn('name_cn', 'export.column.name_cn', required=True, aliases=('mat_CN',), width=34),
            ImportColumn('name_en', 'export.column.name_en', required=True, aliases=('mat_EN',), width=40),
            ImportColumn('model', 'export.column.model', width=22),
            # `spec` 实测最长 286 字符且含换行 —— 列是 `UniversalText`，这里不设长度
            ImportColumn('spec', 'export.column.spec', width=60),
            ImportColumn('brand', 'export.column.brand', width=16),
            ImportColumn('qty', 'export.column.qty', aliases=('amo',), note='import.note.material_number', width=10),
            # 🔴 源表第 10 列的表头是 `"\tunit"`（Excel 脏字符）。框架比对前会 strip，
            # 这里把两种写法都登记出来，免得以后有人去掉 strip 就认不出源文件
            ImportColumn(
                'unit',
                'export.column.unit',
                required=True,
                aliases=('\tunit', 'unit'),
                width=10,
            ),
            ImportColumn('price', 'export.column.price', note='import.note.material_number', width=14),
            ImportColumn(
                'contract_price', 'export.column.contract_price', note='import.note.material_number', width=14
            ),
            ImportColumn('in_price', 'export.column.in_price', note='import.note.material_number', width=14),
            ImportColumn('out_price', 'export.column.out_price', note='import.note.material_number', width=14),
            ImportColumn('market_price', 'export.column.market_price', note='import.note.material_number', width=14),
            ImportColumn('memo', 'export.column.memo', width=20),
            ImportColumn('source', 'export.column.source', width=16),
        ),
        key_of=_material_key,
        validate=_material_validate,
        commit=_material_commit,
        modes=('create', 'upsert', 'update'),
        notes=('import.note.material_source_id', 'import.note.update_keeps_blank'),
    )
)
