from sqlalchemy import Select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.crm.model import Customer
from backend.common.security.data_scope import DataScopedCRUD
from backend.utils.timezone import timezone


class CRUDCustomer(DataScopedCRUD[Customer]):
    """客户数据库操作类

    继承 `DataScopedCRUD` 且**不**写 `data_scope_enabled = False`：读操作自动套上当前用户的数据范围。
    """

    async def get(self, db: AsyncSession, pk: int) -> Customer | None:
        """获取客户详情（受数据范围约束：范围外的当作不存在）"""
        return await self.select_model(db, pk, deleted=0)

    async def get_visible_ids(self, db: AsyncSession, pks: list[int]) -> list[int]:
        """这批 ID 里当前用户看得见的那些（写操作前用它收窄）"""
        rows = await self.select_models(db, id__in=pks, deleted=0)
        return [row.id for row in rows]

    async def get_select(self, name: str | None, phone: str | None, level: int | None, status: int | None) -> Select:
        """分页查询表达式（`select_order` → `select()`，数据范围已经在里面了）"""
        filters = {'deleted': 0}
        if name is not None:
            filters['name__like'] = f'%{name}%'
        if phone is not None:
            filters['phone__like'] = f'%{phone}%'
        if level is not None:
            filters['level'] = level
        if status is not None:
            filters['status'] = status
        return await self.select_order('id', 'desc', **filters)

    async def create(self, db: AsyncSession, data: dict) -> None:
        """创建客户"""
        db.add(self.model(**data))

    async def update(self, db: AsyncSession, pk: int, data: dict) -> int:
        """更新客户（⚠️ 写操作不过数据范围，调用前必须先 `get` 确认看得见）"""
        return await self.update_model_by_column(db, data, id=pk, deleted=0)

    async def delete(self, db: AsyncSession, pks: list[int]) -> int:
        """逻辑删除（⚠️ 同上，`pks` 要先经过 `get_visible_ids`）"""
        return await self.delete_model_by_column(
            db,
            allow_multiple=True,
            logical_deletion=True,
            deleted_flag_column='deleted',
            deleted_flag_value=self.model.id,
            deleted_at_column='deleted_time',
            deleted_at_factory=timezone.now(),
            id__in=pks,
            deleted=0,
        )


customer_dao: CRUDCustomer = CRUDCustomer(Customer)
