from datetime import datetime
from decimal import Decimal

from pydantic import ConfigDict, Field

from backend.common.schema import ColumnLengthChecked, SchemaBase
from backend.plugin.pm.model.material import PmMaterial

# ── PmMaterial ───────────────────────────────────────────────────────────────────────


class PmMaterialSchemaBase(SchemaBase):
    source_id: int | None = Field(None, description='来源 Excel 行 ID（导入幂等键）')
    kind: str = Field(description='类型（PLC / Program（编程/软件）/ Sensor（现场安装））')
    category: str = Field(description='类别')
    name_cn: str = Field(description='材料中文名')
    name_en: str = Field(description='材料英文名')
    model: str | None = Field(None, description='型号')
    spec: str | None = Field(None, description='规格描述')
    brand: str | None = Field(None, description='品牌')
    qty: Decimal | None = Field(None, description='合同数量')
    unit: str = Field(description='单位')
    price: Decimal | None = Field(None, description='合同单价')
    contract_price: Decimal | None = Field(None, description='合同合价')
    in_price: Decimal | None = Field(None, description='报入单价')
    out_price: Decimal | None = Field(None, description='报出价')
    market_price: Decimal | None = Field(None, description='市场价')
    memo: str | None = Field(None, description='备注')
    source: str | None = Field(None, description='来源')
    currency: str = Field('RMB', description='币种')
    active: bool = Field(True, description='是否启用')


class CreatePmMaterialParam(ColumnLengthChecked, PmMaterialSchemaBase):
    __sa_model__ = PmMaterial


class UpdatePmMaterialParam(ColumnLengthChecked, SchemaBase):
    __sa_model__ = PmMaterial

    source_id: int | None = Field(None, description='来源 Excel 行 ID（导入幂等键）')
    kind: str | None = Field(None, description='类型')
    category: str | None = Field(None, description='类别')
    name_cn: str | None = Field(None, description='材料中文名')
    name_en: str | None = Field(None, description='材料英文名')
    model: str | None = Field(None, description='型号')
    spec: str | None = Field(None, description='规格描述')
    brand: str | None = Field(None, description='品牌')
    qty: Decimal | None = Field(None, description='合同数量')
    unit: str | None = Field(None, description='单位')
    price: Decimal | None = Field(None, description='合同单价')
    contract_price: Decimal | None = Field(None, description='合同合价')
    in_price: Decimal | None = Field(None, description='报入单价')
    out_price: Decimal | None = Field(None, description='报出价')
    market_price: Decimal | None = Field(None, description='市场价')
    memo: str | None = Field(None, description='备注')
    source: str | None = Field(None, description='来源')
    currency: str | None = Field(None, description='币种')
    active: bool | None = Field(None, description='是否启用')


class DeletePmMaterialParam(SchemaBase):
    pks: list[int] = Field(description='材料 ID 列表')


class GetPmMaterialDetail(SchemaBase):
    model_config = ConfigDict(from_attributes=True)

    id: int = Field(description='材料 ID')
    source_id: int | None = Field(None, description='来源 Excel 行 ID')
    kind: str = Field(description='类型')
    category: str = Field(description='类别')
    name_cn: str = Field(description='材料中文名')
    name_en: str = Field(description='材料英文名')
    model: str | None = Field(None, description='型号')
    spec: str | None = Field(None, description='规格描述')
    brand: str | None = Field(None, description='品牌')
    qty: Decimal | None = Field(None, description='合同数量')
    unit: str = Field(description='单位')
    price: Decimal | None = Field(None, description='合同单价')
    contract_price: Decimal | None = Field(None, description='合同合价')
    in_price: Decimal | None = Field(None, description='报入单价')
    out_price: Decimal | None = Field(None, description='报出价')
    market_price: Decimal | None = Field(None, description='市场价')
    memo: str | None = Field(None, description='备注')
    source: str | None = Field(None, description='来源')
    currency: str = Field(description='币种')
    active: bool = Field(description='是否启用')
    created_time: datetime = Field(description='创建时间')
    updated_time: datetime | None = Field(None, description='更新时间')
