"""WIR (Work Inspection Request) Ledger models.

Two tables:
  wir_record — 一份 WIR 提交/批复记录一行，跨 DC 合并台账
  wir_type   — WIR 类型参考表（桥架安装 / 线管安装 / DDC 控制柜 …）中英对照
"""

from datetime import datetime

import sqlalchemy as sa

from sqlalchemy.orm import Mapped, mapped_column

from backend.common.enums import DataBaseType
from backend.common.model import Base, TimeZone, UniversalStr, UniversalText, id_key
from backend.core.conf import settings

# `tml_no` 可空（289 行里 243 行没有 TML 号），而 SQL Server 的 UNIQUE 约束
# 认为多个 NULL 彼此相等 —— 普通唯一约束下第二条空 TML 的记录会被拒绝。
# 同 `app/admin/model/user.py` 的 `_EMAIL_UNIQUE`，SQL Server 下改用筛选唯一索引。
_TML_NO_UNIQUE = (
    sa.Index(
        'uk_wir_record_tml_no_deleted',
        'tml_no',
        'deleted',
        unique=True,
        mssql_where=sa.text('tml_no IS NOT NULL'),
    )
    if DataBaseType.sqlserver == settings.DATABASE_TYPE
    else sa.UniqueConstraint('tml_no', 'deleted', name='uk_wir_record_tml_no_deleted')
)


class WirType(Base):
    """WIR 类型参考表"""

    __tablename__ = 'wir_type'
    __table_args__ = ({'comment': 'WIR 类型参考表（中英对照）'},)

    id: Mapped[id_key] = mapped_column(init=False)
    type_cn: Mapped[str] = mapped_column(UniversalStr(128), comment='类型中文名')
    type_en: Mapped[str] = mapped_column(UniversalStr(256), comment='类型英文名')


class WirRecord(Base):
    """WIR 台账主表"""

    __tablename__ = 'wir_record'
    __table_args__ = (
        _TML_NO_UNIQUE,
        {'comment': 'WIR 台账主表'},
    )

    id: Mapped[id_key] = mapped_column(init=False)
    #: 源 Excel 的行 ID（`WIR Ledger_toDB.xlsx` 的 `ID` 列）。导入时拿它当幂等键：
    #: 289 行里有 243 行没有 TML 号，也没有一个「同一行」的业务键
    source_id: Mapped[int | None] = mapped_column(
        sa.BigInteger, default=None, index=True, comment='来源 Excel 行 ID（导入幂等键）'
    )
    from_party: Mapped[str | None] = mapped_column(UniversalStr(64), default=None, comment='提交方（如 DRT）')
    tml_no: Mapped[str | None] = mapped_column(
        UniversalStr(128), default=None, index=True, comment='TML 申请编号（进 PMWeb 之前）'
    )
    pmweb_no: Mapped[str | None] = mapped_column(
        UniversalStr(256), default=None, index=True, comment='PMWeb 正式编号（顾问系统号）'
    )
    doc_type: Mapped[str | None] = mapped_column(UniversalStr(16), default=None, comment='文件类型（WIR / MIR）')
    discipline: Mapped[str | None] = mapped_column(
        UniversalStr(16), default=None, index=True, comment='专业（BMS / SEC / ELV）'
    )
    description: Mapped[str | None] = mapped_column(UniversalText, default=None, comment='检查内容描述')
    drt_submitted: Mapped[datetime | None] = mapped_column(TimeZone, default=None, comment='DRT 提交日期')
    pmx_submitted: Mapped[datetime | None] = mapped_column(TimeZone, default=None, comment='PMX 提交日期')
    cb_inspection: Mapped[datetime | None] = mapped_column(TimeZone, default=None, comment='C&B 顾问检查日期')
    doc_status: Mapped[str | None] = mapped_column(
        UniversalStr(64), default=None, index=True, comment='文件批复状态（Approved / Approved as Noted）'
    )
    comment: Mapped[str | None] = mapped_column(UniversalText, default=None, comment='顾问意见')
    another_desc: Mapped[str | None] = mapped_column(UniversalStr(512), default=None, comment='别称/中文描述')
    dc: Mapped[str | None] = mapped_column(
        UniversalStr(32), default=None, index=True, comment='所属 DC（DC1-Fitout / DC2-Fitout / DC3-Fitout）'
    )
    filepath: Mapped[str | None] = mapped_column(
        UniversalStr(1024), default=None, comment='签字件路径（文件名 → 目录）'
    )

    # FK to wir_type（不做 relationship：列表页按 type_id 批量补中英文名，
    # 关系属性在 `paging_data()` 序列化时会被惰性加载，asyncpg 已离开 greenlet 上下文 → 500）
    type_id: Mapped[int | None] = mapped_column(
        sa.BigInteger, sa.ForeignKey('wir_type.id', ondelete='SET NULL'), default=None, comment='WIR 类型 ID'
    )
