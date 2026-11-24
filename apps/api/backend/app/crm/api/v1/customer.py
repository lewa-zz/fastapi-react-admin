from typing import Annotated

from fastapi import APIRouter, Depends, Path, Query, Request

from backend.app.crm.schema.customer import (
    CreateCustomerParam,
    DeleteCustomerParam,
    GetCustomerDetail,
    UpdateCustomerParam,
)
from backend.app.crm.service.customer_service import customer_service
from backend.common.pagination import DependsPagination, PageData
from backend.common.response.response_schema import (
    ResponseModel,
    ResponseSchemaModel,
    response_base,
)
from backend.common.security.permission import RequestPermission
from backend.common.security.rbac import DependsRBAC
from backend.database.db import CurrentSession, CurrentSessionTransaction

router = APIRouter()


@router.get(
    '/{pk}',
    summary='获取客户详情',
    dependencies=[Depends(RequestPermission('crm:customer:list')), DependsRBAC],
)
async def get_customer(
    db: CurrentSession, pk: Annotated[int, Path(description='客户 ID')]
) -> ResponseSchemaModel[GetCustomerDetail]:
    data = await customer_service.get(db=db, pk=pk)
    return response_base.success(data=data)


@router.get(
    '',
    summary='分页获取客户',
    dependencies=[
        Depends(RequestPermission('crm:customer:list')),
        DependsRBAC,
        DependsPagination,
    ],
)
async def get_customers_paginated(
    db: CurrentSession,
    name: Annotated[str | None, Query(description='客户名称')] = None,
    phone: Annotated[str | None, Query(description='联系电话')] = None,
    level: Annotated[int | None, Query(description='客户等级')] = None,
    status: Annotated[int | None, Query(description='状态')] = None,
) -> ResponseSchemaModel[PageData[GetCustomerDetail]]:
    page_data = await customer_service.get_list(db=db, name=name, phone=phone, level=level, status=status)
    return response_base.success(data=page_data)


@router.post(
    '',
    summary='创建客户',
    dependencies=[Depends(RequestPermission('crm:customer:add')), DependsRBAC],
)
async def create_customer(request: Request, db: CurrentSessionTransaction, obj: CreateCustomerParam) -> ResponseModel:
    await customer_service.create(db=db, obj=obj, user=request.user)
    return response_base.success()


@router.put(
    '/{pk}',
    summary='更新客户',
    dependencies=[Depends(RequestPermission('crm:customer:edit')), DependsRBAC],
)
async def update_customer(
    db: CurrentSessionTransaction,
    pk: Annotated[int, Path(description='客户 ID')],
    obj: UpdateCustomerParam,
) -> ResponseModel:
    await customer_service.update(db=db, pk=pk, obj=obj)
    return response_base.success()


@router.delete(
    '',
    summary='批量删除客户',
    dependencies=[Depends(RequestPermission('crm:customer:del')), DependsRBAC],
)
async def delete_customers(db: CurrentSessionTransaction, obj: DeleteCustomerParam) -> ResponseModel:
    await customer_service.delete(db=db, obj=obj)
    return response_base.success()
