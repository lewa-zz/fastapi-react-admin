from datetime import datetime

from pydantic import ConfigDict, Field

from backend.common.schema import ColumnLengthChecked, SchemaBase
from backend.plugin.wir.model.wir import WirRecord, WirType

# ── WirType ──────────────────────────────────────────────────────────────────────────


class CreateWirTypeParam(ColumnLengthChecked, SchemaBase):
    __sa_model__ = WirType

    type_cn: str = Field(description='类型中文名')
    type_en: str = Field(description='类型英文名')


class UpdateWirTypeParam(ColumnLengthChecked, SchemaBase):
    __sa_model__ = WirType

    type_cn: str = Field(description='类型中文名')
    type_en: str = Field(description='类型英文名')


class GetWirTypeDetail(SchemaBase):
    model_config = ConfigDict(from_attributes=True)

    id: int = Field(description='类型 ID')
    type_cn: str = Field(description='类型中文名')
    type_en: str = Field(description='类型英文名')


# ── WirRecord ────────────────────────────────────────────────────────────────────────


class WirRecordSchemaBase(SchemaBase):
    from_party: str | None = Field(None, description='提交方')
    tml_no: str | None = Field(None, description='TML 申请编号')
    pmweb_no: str | None = Field(None, description='PMWeb 正式编号')
    doc_type: str | None = Field(None, description='文件类型（WIR / MIR）')
    discipline: str | None = Field(None, description='专业（BMS / SEC / ELV）')
    description: str | None = Field(None, description='检查内容描述')
    drt_submitted: datetime | None = Field(None, description='DRT 提交日期')
    pmx_submitted: datetime | None = Field(None, description='PMX 提交日期')
    cb_inspection: datetime | None = Field(None, description='C&B 检查日期')
    doc_status: str | None = Field(None, description='文件批复状态')
    comment: str | None = Field(None, description='顾问意见')
    another_desc: str | None = Field(None, description='别称/中文描述')
    dc: str | None = Field(None, description='所属 DC')
    filepath: str | None = Field(None, description='签字件路径')
    type_id: int | None = Field(None, description='WIR 类型 ID')


class CreateWirRecordParam(ColumnLengthChecked, WirRecordSchemaBase):
    __sa_model__ = WirRecord


class UpdateWirRecordParam(ColumnLengthChecked, SchemaBase):
    __sa_model__ = WirRecord

    from_party: str | None = Field(None, description='提交方')
    tml_no: str | None = Field(None, description='TML 申请编号')
    pmweb_no: str | None = Field(None, description='PMWeb 正式编号')
    doc_type: str | None = Field(None, description='文件类型（WIR / MIR）')
    discipline: str | None = Field(None, description='专业（BMS / SEC / ELV）')
    description: str | None = Field(None, description='检查内容描述')
    drt_submitted: datetime | None = Field(None, description='DRT 提交日期')
    pmx_submitted: datetime | None = Field(None, description='PMX 提交日期')
    cb_inspection: datetime | None = Field(None, description='C&B 检查日期')
    doc_status: str | None = Field(None, description='文件批复状态')
    comment: str | None = Field(None, description='顾问意见')
    another_desc: str | None = Field(None, description='别称/中文描述')
    dc: str | None = Field(None, description='所属 DC')
    filepath: str | None = Field(None, description='签字件路径')
    type_id: int | None = Field(None, description='WIR 类型 ID')


class DeleteWirRecordParam(SchemaBase):
    pks: list[int] = Field(description='WIR 记录 ID 列表')


class GetWirRecordDetail(SchemaBase):
    model_config = ConfigDict(from_attributes=True)

    id: int = Field(description='WIR 记录 ID')
    from_party: str | None = Field(None, description='提交方')
    tml_no: str | None = Field(None, description='TML 申请编号')
    pmweb_no: str | None = Field(None, description='PMWeb 正式编号')
    doc_type: str | None = Field(None, description='文件类型')
    discipline: str | None = Field(None, description='专业')
    description: str | None = Field(None, description='检查内容描述')
    drt_submitted: datetime | None = Field(None, description='DRT 提交日期')
    pmx_submitted: datetime | None = Field(None, description='PMX 提交日期')
    cb_inspection: datetime | None = Field(None, description='C&B 检查日期')
    doc_status: str | None = Field(None, description='文件批复状态')
    comment: str | None = Field(None, description='顾问意见')
    another_desc: str | None = Field(None, description='别称/中文描述')
    dc: str | None = Field(None, description='所属 DC')
    filepath: str | None = Field(None, description='签字件路径')
    type_id: int | None = Field(None, description='WIR 类型 ID')
    type_cn: str | None = Field(None, description='类型中文名（join wir_type）')
    type_en: str | None = Field(None, description='类型英文名（join wir_type）')
    created_time: datetime = Field(description='创建时间')
    updated_time: datetime | None = Field(None, description='更新时间')
