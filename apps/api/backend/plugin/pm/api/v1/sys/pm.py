from typing import Annotated

from fastapi import APIRouter, Depends, Path, Query

from backend.common.pagination import DependsPagination, PageData
from backend.common.response.response_schema import ResponseModel, ResponseSchemaModel, response_base
from backend.common.security.permission import RequestPermission
from backend.common.security.rbac import DependsRBAC
from backend.database.db import CurrentSession, CurrentSessionTransaction
from backend.plugin.pm.schema.material import (
    CreatePmMaterialParam,
    DeletePmMaterialParam,
    GetPmMaterialDetail,
    UpdatePmMaterialParam,
)
from backend.plugin.pm.service.material_service import pm_service

# ⚠️ 最终路径是 `/api/v1/sys/pm/materials`（扩展级插件的 `[api.pm] prefix = "/pm"`
# 挂在 admin 的 `/api/v1/sys` 路由下），不是 `/api/v1/pm/materials`。
router = APIRouter()

# ── PmMaterial ───────────────────────────────────────────────────────────────────────
# 路由声明顺序：`/materials` 在 `/materials/{pk}` 之前。静态路径放到后面会被
# `pk` 吞掉（报 `422 pk 不是合法整数`）。


@router.get(
    '/materials',
    summary='分页获取材料主数据',
    dependencies=[Depends(RequestPermission('pm:material:list')), DependsRBAC, DependsPagination],
)
async def get_pm_materials(
    db: CurrentSession,
    kind: Annotated[str | None, Query(description='类型')] = None,
    category: Annotated[str | None, Query(description='类别')] = None,
    brand: Annotated[str | None, Query(description='品牌')] = None,
    active: Annotated[bool | None, Query(description='是否启用（不传 = 全部）')] = None,
    search: Annotated[str | None, Query(description='搜索（中文名 / 英文名 / 型号 / 规格）')] = None,
) -> ResponseSchemaModel[PageData[GetPmMaterialDetail]]:
    page_data = await pm_service.get_material_list(
        db=db, kind=kind, category=category, brand=brand, active=active, search=search
    )
    return response_base.success(data=page_data)


@router.get(
    '/materials/{pk}',
    summary='获取材料详情',
    dependencies=[Depends(RequestPermission('pm:material:list')), DependsRBAC],
)
async def get_pm_material(
    db: CurrentSession, pk: Annotated[int, Path(description='材料 ID')]
) -> ResponseSchemaModel[GetPmMaterialDetail]:
    data = await pm_service.get_material(db=db, pk=pk)
    return response_base.success(data=data)


@router.post(
    '/materials',
    summary='创建材料',
    dependencies=[Depends(RequestPermission('pm:material:add')), DependsRBAC],
)
async def create_pm_material(
    db: CurrentSessionTransaction, obj: CreatePmMaterialParam
) -> ResponseSchemaModel[GetPmMaterialDetail]:
    material = await pm_service.create_material(db=db, obj=obj)
    return response_base.success(data=GetPmMaterialDetail.model_validate(material))


@router.put(
    '/materials/{pk}',
    summary='更新材料',
    dependencies=[Depends(RequestPermission('pm:material:edit')), DependsRBAC],
)
async def update_pm_material(
    db: CurrentSessionTransaction,
    pk: Annotated[int, Path(description='材料 ID')],
    obj: UpdatePmMaterialParam,
) -> ResponseModel:
    count = await pm_service.update_material(db=db, pk=pk, obj=obj)
    if count > 0:
        return response_base.success()
    return response_base.fail()


@router.delete(
    '/materials',
    summary='批量删除材料',
    dependencies=[Depends(RequestPermission('pm:material:del')), DependsRBAC],
)
async def delete_pm_materials(db: CurrentSessionTransaction, obj: DeletePmMaterialParam) -> ResponseModel:
    count = await pm_service.delete_materials(db=db, obj=obj)
    if count > 0:
        return response_base.success()
    return response_base.fail()
