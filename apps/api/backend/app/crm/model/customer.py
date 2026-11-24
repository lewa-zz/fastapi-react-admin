import sqlalchemy as sa

from sqlalchemy.orm import Mapped, mapped_column

from backend.common.model import Base, UniversalStr, UniversalText, id_key


class Customer(Base):
    """客户表"""

    __tablename__ = 'crm_customer'
    __table_args__ = {'comment': '客户表'}

    id: Mapped[id_key] = mapped_column(init=False)
    name: Mapped[str] = mapped_column(UniversalStr(64), comment='客户名称')
    phone: Mapped[str | None] = mapped_column(UniversalStr(20), default=None, comment='联系电话')
    level: Mapped[int] = mapped_column(default=0, comment='客户等级（0：普通、1：重要、2：VIP）')
    status: Mapped[int] = mapped_column(default=1, comment='状态（0：停用、1：正常）')
    # 数据权限靠这两列落地：规则里的 `__dept_id__` / `__created_by__` 解析成同名列，表上没有，规则就落不下来
    dept_id: Mapped[int | None] = mapped_column(sa.BigInteger, default=None, index=True, comment='所属部门 ID')
    owner_id: Mapped[int | None] = mapped_column(sa.BigInteger, default=None, comment='负责人用户 ID')
    created_by: Mapped[int] = mapped_column(sa.BigInteger, default=0, index=True, comment='创建者用户 ID')
    remark: Mapped[str | None] = mapped_column(UniversalText, default=None, comment='备注')
