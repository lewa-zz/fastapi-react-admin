from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.crm.crud.crud_customer import customer_dao
from backend.app.crm.model import Customer
from backend.app.crm.schema.customer import (
    CreateCustomerParam,
    DeleteCustomerParam,
    UpdateCustomerParam,
)
from backend.common.exception import errors
from backend.common.i18n import t
from backend.common.pagination import paging_data


class CustomerService:
    """客户服务类"""

    @staticmethod
    async def get(*, db: AsyncSession, pk: int) -> Customer:
        customer = await customer_dao.get(db, pk)
        if not customer:
            raise errors.NotFoundError(msg=t('error.customer.not_found'))
        return customer

    @staticmethod
    async def get_list(
        *, db: AsyncSession, name: str | None, phone: str | None, level: int | None, status: int | None
    ) -> dict[str, Any]:
        customer_select = await customer_dao.get_select(name=name, phone=phone, level=level, status=status)
        return await paging_data(db, customer_select)

    @staticmethod
    async def create(*, db: AsyncSession, obj: CreateCustomerParam, user: Any) -> None:
        data = obj.model_dump()
        # 不传就归到创建人自己的部门 / 名下 —— 否则 dept_id 是空，「本部门」规则下谁都看不见它
        data['dept_id'] = data['dept_id'] or user.dept_id
        data['owner_id'] = data['owner_id'] or user.id
        data['created_by'] = user.id
        await customer_dao.create(db, data)

    @staticmethod
    async def update(*, db: AsyncSession, pk: int, obj: UpdateCustomerParam) -> int:
        # 先过一次受范围约束的读：范围外的客户在这里就是 404，不会被改到
        if not await customer_dao.get(db, pk):
            raise errors.NotFoundError(msg=t('error.customer.not_found'))
        # exclude_unset：没传的字段不写。否则只改名字的请求会把 dept_id / owner_id 冲成 NULL
        return await customer_dao.update(db, pk, obj.model_dump(exclude_unset=True))

    @staticmethod
    async def delete(*, db: AsyncSession, obj: DeleteCustomerParam) -> int:
        visible = await customer_dao.get_visible_ids(db, obj.pks)
        if not visible:
            return 0
        return await customer_dao.delete(db, visible)


customer_service: CustomerService = CustomerService()
