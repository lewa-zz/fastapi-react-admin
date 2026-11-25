from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends, File, Path, Query, Request, UploadFile
from fastapi.responses import Response

from backend.app.admin.schema.data_import import (
    ImportCommitDetail,
    ImportCommitParam,
    ImportModeParam,
    ImportPreviewDetail,
)
from backend.app.admin.schema.export_job import GetExportJobDetail, StartExportParam
from backend.app.admin.service.export_service import export_service
from backend.app.admin.service.import_service import import_service
from backend.common.pagination import DependsPagination, PageData
from backend.common.response.response_schema import ResponseModel, ResponseSchemaModel, response_base
from backend.common.security.permission import RequestPermission
from backend.common.security.rbac import DependsRBAC
from backend.database.db import CurrentSession, CurrentSessionTransaction
from backend.plugin.materials.dataio import MATERIAL_EXPORT, MATERIAL_IMPORT
from backend.plugin.materials.schema.material import (
    CreatePmMaterialParam,
    DeletePmMaterialParam,
    GetPmMaterialDetail,
    UpdatePmMaterialParam,
)
from backend.plugin.materials.service.material_service import pm_service
from backend.utils.excel_ops import read_table_upload, xlsx_attachment

# 最终路径是 `/api/v1/sys/materials`（扩展级插件，prefix="/materials" 挂在 admin 的 /sys 下）
router = APIRouter()

# ── 导入 / 导出 ──────────────────────────────────────────────────────────────────────
# ⚠️ 路由声明顺序：`/import/*` 和 `/export` 都在 `GET /{pk}` **之前**。
# 两段路径现在撞不上，但以后加一条一段的放到后面就会被 `pk` 吞掉，报
# `422 pk 不是合法整数` —— 看着像参数写错了，查起来没有方向（同 `plugin/wir/api/v1/sys/wir.py`）


@router.get(
    '/import/template',
    summary='下载材料导入模板',
    dependencies=[Depends(RequestPermission('pm:material:import')), DependsRBAC],
)
async def download_material_import_template(db: CurrentSession) -> Response:
    raw, name = await import_service.template(db=db, spec=MATERIAL_IMPORT)
    return xlsx_attachment(raw, name)


@router.post(
    '/import/preview',
    summary='预览材料导入',
    dependencies=[Depends(RequestPermission('pm:material:import')), DependsRBAC],
)
async def preview_material_import(
    request: Request,
    db: CurrentSession,
    file: Annotated[UploadFile, File(description='xlsx 文件')],
    mode: Annotated[
        ImportModeParam, Query(description='导入模式（create：只新增、upsert：新增并更新、update：只更新）')
    ] = 'create',
) -> ResponseSchemaModel[ImportPreviewDetail]:
    raw = await read_table_upload(file)
    data = await import_service.preview(db=db, spec=MATERIAL_IMPORT, raw=raw, user=request.user, mode=mode)
    return response_base.success(data=data)


@router.post(
    '/import/commit',
    summary='提交材料导入',
    dependencies=[Depends(RequestPermission('pm:material:import')), DependsRBAC],
)
async def commit_material_import(
    request: Request, db: CurrentSession, background_tasks: BackgroundTasks, obj: ImportCommitParam
) -> ResponseSchemaModel[ImportCommitDetail]:
    # 不用 `CurrentSessionTransaction`：全有或全无要能整批回滚，事务由 service 自己收
    data = await import_service.commit(
        db=db, spec=MATERIAL_IMPORT, user=request.user, obj=obj, background_tasks=background_tasks
    )
    return response_base.success(data=data)


@router.post(
    '/export',
    summary='导出材料',
    dependencies=[Depends(RequestPermission('pm:material:export')), DependsRBAC],
)
async def export_materials(
    request: Request, db: CurrentSession, obj: StartExportParam
) -> ResponseSchemaModel[GetExportJobDetail]:
    # 小批量当场生成完才返回（status=2，前端直接下载）；大批量返回排队（status=0），生成完发站内消息
    data = await export_service.start(db=db, request=request, spec=MATERIAL_EXPORT, obj=obj)
    return response_base.success(data=data)


# ── PmMaterial ───────────────────────────────────────────────────────────────────────


@router.get(
    '',
    summary='分页获取材料主数据',
    dependencies=[Depends(RequestPermission('pm:material:list')), DependsRBAC, DependsPagination],
)
async def get_materials(
    db: CurrentSession,
    kind: Annotated[str | None, Query(description='类型')] = None,
    category: Annotated[str | None, Query(description='类别')] = None,
    brand: Annotated[str | None, Query(description='品牌')] = None,
    active: Annotated[bool | None, Query(description='是否启用（不传=全部）')] = None,
    search: Annotated[str | None, Query(description='搜索（中文名/英文名/型号/规格）')] = None,
) -> ResponseSchemaModel[PageData[GetPmMaterialDetail]]:
    page_data = await pm_service.get_material_list(
        db=db, kind=kind, category=category, brand=brand, active=active, search=search
    )
    return response_base.success(data=page_data)


@router.get(
    '/{pk}',
    summary='获取材料详情',
    dependencies=[Depends(RequestPermission('pm:material:list')), DependsRBAC],
)
async def get_material(
    db: CurrentSession, pk: Annotated[int, Path(description='材料 ID')]
) -> ResponseSchemaModel[GetPmMaterialDetail]:
    data = await pm_service.get_material(db=db, pk=pk)
    return response_base.success(data=data)


@router.post(
    '',
    summary='创建材料',
    dependencies=[Depends(RequestPermission('pm:material:add')), DependsRBAC],
)
async def create_material(
    db: CurrentSessionTransaction, obj: CreatePmMaterialParam
) -> ResponseSchemaModel[GetPmMaterialDetail]:
    material = await pm_service.create_material(db=db, obj=obj)
    return response_base.success(data=GetPmMaterialDetail.model_validate(material))


@router.put(
    '/{pk}',
    summary='更新材料',
    dependencies=[Depends(RequestPermission('pm:material:edit')), DependsRBAC],
)
async def update_material(
    db: CurrentSessionTransaction,
    pk: Annotated[int, Path(description='材料 ID')],
    obj: UpdatePmMaterialParam,
) -> ResponseModel:
    count = await pm_service.update_material(db=db, pk=pk, obj=obj)
    if count > 0:
        return response_base.success()
    return response_base.fail()


@router.delete(
    '',
    summary='批量删除材料',
    dependencies=[Depends(RequestPermission('pm:material:del')), DependsRBAC],
)
async def delete_materials(db: CurrentSessionTransaction, obj: DeletePmMaterialParam) -> ResponseModel:
    count = await pm_service.delete_materials(db=db, obj=obj)
    if count > 0:
        return response_base.success()
    return response_base.fail()
