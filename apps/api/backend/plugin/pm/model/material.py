"""PM 材料主数据模型。

表 `pm_material` 的字段**全部来自桌面 Excel 实测**（`/Users/rico/Desktop/材料表.xlsx`，
sheet `Material`，100 条 + 1 行合计跳过），不是从 wir-system 的 SQLModel 抄的：

- 表头第 10 列实际是 `"\tunit"`（Excel 脏字符），库列名用 `unit`
- `type` 是 Python 保留字，列名用 `kind`
- `spec` 最长 286 字符且含换行 → `UniversalText`，用 `UniversalStr` 会截断
- 金额一律 `Numeric(14, 4)` + `Mapped[Decimal | None]`：`Mapped[float]` 在
  SQLAlchemy 2.1 会映射成 `Double`，SQL Server 上 `test_model_matches_migrations` 会红

🔴 **不要给这个模型加 relationship。** `paging_data()` 序列化会碰未加载的关系属性 →
SQLAlchemy 惰性加载 → asyncpg 已经离开 greenlet 上下文 → `MissingGreenlet` → 列表 500
（WIR 的 `wir_type` 就是这么踩的）。
"""

from decimal import Decimal

import sqlalchemy as sa

from sqlalchemy.orm import Mapped, mapped_column

from backend.common.enums import DataBaseType
from backend.common.model import Base, UniversalStr, UniversalText, id_key
from backend.core.conf import settings

# `source_id` 可空（CRUD 手工建的材料没有源 Excel 行 ID），而 SQL Server 的 UNIQUE
# 约束认为多个 NULL 彼此相等 —— 普通唯一约束下第二条没有 source_id 的材料插不进去。
# 写法同 `plugin/wir/model/wir.py` 的 `_TML_NO_UNIQUE` / `app/admin/model/user.py` 的
# `_EMAIL_UNIQUE`：SQL Server 下改用只对非 NULL 生效的筛选唯一索引。
_SOURCE_ID_UNIQUE = (
    sa.Index(
        'uk_pm_material_source_id_deleted',
        'source_id',
        'deleted',
        unique=True,
        mssql_where=sa.text('source_id IS NOT NULL'),
    )
    if DataBaseType.sqlserver == settings.DATABASE_TYPE
    else sa.UniqueConstraint('source_id', 'deleted', name='uk_pm_material_source_id_deleted')
)


class PmMaterial(Base):
    """BKK03 材料主数据"""

    __tablename__ = 'pm_material'
    __table_args__ = (
        _SOURCE_ID_UNIQUE,
        # 列表页常态是「按类别筛 + 只看启用」，单列索引加这条组合索引一起服务
        sa.Index('ix_pm_material_category_active', 'category', 'active'),
        {'comment': 'BKK03 材料主数据'},
    )

    # ⚠️ 列的**声明顺序**由 `MappedAsDataclass` 的规则约束：带默认值的列不能排在
    # 不带默认值的列前面（否则 `non-default argument follows default argument`）。
    # `id` 靠 `sort_order=-999` 排在最前，其余按「必填 → 可空 → 带默认值」排。
    id: Mapped[id_key] = mapped_column(init=False)
    #: Excel 的 `type` 列。`type` 是 Python 保留字，列名只能叫 `kind`。
    #: 值原样存（`PLC` / `Program（编程/软件）` / `Sensor（现场安装）`），实测最长 14
    kind: Mapped[str] = mapped_column(UniversalStr(64), comment='类型（PLC / Program（编程/软件）…）')
    category: Mapped[str] = mapped_column(UniversalStr(64), index=True, comment='类别（BMS控制柜 …）')
    name_cn: Mapped[str] = mapped_column(UniversalStr(128), comment='材料中文名')
    name_en: Mapped[str] = mapped_column(UniversalStr(256), comment='材料英文名')
    unit: Mapped[str] = mapped_column(UniversalStr(32), comment='单位（台/件、套、米…）')
    #: 源 Excel 的 `id` 列（1..100）。导入幂等键：同一份材料表导入两次不重复。
    #: 现在 CRUD 可空 —— 手工新增的材料没有源行 ID
    source_id: Mapped[int | None] = mapped_column(sa.BigInteger, default=None, comment='来源 Excel 行 ID（导入幂等键）')
    model: Mapped[str | None] = mapped_column(UniversalStr(64), default=None, comment='型号')
    spec: Mapped[str | None] = mapped_column(UniversalText, default=None, comment='规格描述（含换行）')
    brand: Mapped[str | None] = mapped_column(UniversalStr(64), default=None, index=True, comment='品牌')
    qty: Mapped[Decimal | None] = mapped_column(sa.Numeric(14, 4), default=None, comment='合同数量')
    price: Mapped[Decimal | None] = mapped_column(sa.Numeric(14, 4), default=None, comment='合同单价')
    contract_price: Mapped[Decimal | None] = mapped_column(sa.Numeric(14, 4), default=None, comment='合同合价')
    in_price: Mapped[Decimal | None] = mapped_column(sa.Numeric(14, 4), default=None, comment='报入单价')
    out_price: Mapped[Decimal | None] = mapped_column(sa.Numeric(14, 4), default=None, comment='报出价')
    market_price: Mapped[Decimal | None] = mapped_column(sa.Numeric(14, 4), default=None, comment='市场价')
    memo: Mapped[str | None] = mapped_column(UniversalStr(256), default=None, comment='备注')
    source: Mapped[str | None] = mapped_column(UniversalStr(128), default=None, comment='来源')
    currency: Mapped[str] = mapped_column(UniversalStr(8), default='RMB', server_default='RMB', comment='币种')
    active: Mapped[bool] = mapped_column(default=True, index=True, comment='是否启用（停用不出现在候选里）')
