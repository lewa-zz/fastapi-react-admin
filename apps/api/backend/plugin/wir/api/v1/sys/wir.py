from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends, File, Path, Query, Request, UploadFile
from fastapi.responses import Response

from backend.app.admin.schema.data_import import (
    ImportCommitDetail,
    ImportCommitParam,
    ImportModeParam,
    ImportPreviewDetail,
)
from backend.app.admin.service.import_service import import_service
from backend.common.pagination import DependsPagination, PageData
from backend.common.response.response_schema import ResponseModel, ResponseSchemaModel, response_base
from backend.common.security.jwt import DependsJwtAuth
from backend.common.security.permission import RequestPermission
from backend.common.security.rbac import DependsRBAC
from backend.database.db import CurrentSession, CurrentSessionTransaction
from backend.plugin.wir.dataio import WIR_RECORD_IMPORT, WIR_TYPE_IMPORT
from backend.plugin.wir.schema.wir import (
    CreateWirRecordParam,
    CreateWirTypeParam,
    DeleteWirRecordParam,
    GetWirRecordDetail,
    GetWirTypeDetail,
    UpdateWirRecordParam,
    UpdateWirTypeParam,
)
from backend.plugin.wir.service.wir_service import wir_service
from backend.utils.excel_ops import read_table_upload, xlsx_attachment

router = APIRouter()

# ── 导入 ────────────────────────────────────────────────────────────────────────────
# ⚠️ 路由声明顺序：`/import/*` 都在 `GET /{pk}` 之前。两段路径现在撞不上，但以后
# 加一条一段的放到后面就会被 `pk` 吞掉（报 `422 pk 不是合法整数`）


@router.get(
    '/types/import/template',
    summary='下载 WIR 类型导入模板',
    dependencies=[Depends(RequestPermission('wir:import')), DependsRBAC],
)
async def download_wir_type_import_template(db: CurrentSession) -> Response:
    raw, name = await import_service.template(db=db, spec=WIR_TYPE_IMPORT)
    return xlsx_attachment(raw, name)


@router.post(
    '/types/import/preview',
    summary='预览 WIR 类型导入',
    dependencies=[Depends(RequestPermission('wir:import')), DependsRBAC],
)
async def preview_wir_type_import(
    request: Request,
    db: CurrentSession,
    file: Annotated[UploadFile, File(description='xlsx 文件')],
    mode: Annotated[ImportModeParam, Query(description='导入模式（create：只新增、upsert：新增并更新）')] = 'create',
) -> ResponseSchemaModel[ImportPreviewDetail]:
    raw = await read_table_upload(file)
    data = await import_service.preview(db=db, spec=WIR_TYPE_IMPORT, raw=raw, user=request.user, mode=mode)
    return response_base.success(data=data)


@router.post(
    '/types/import/commit',
    summary='提交 WIR 类型导入',
    dependencies=[Depends(RequestPermission('wir:import')), DependsRBAC],
)
async def commit_wir_type_import(
    request: Request, db: CurrentSession, background_tasks: BackgroundTasks, obj: ImportCommitParam
) -> ResponseSchemaModel[ImportCommitDetail]:
    # 不用 `CurrentSessionTransaction`：全有或全无要能整批回滚，事务由 service 自己收
    data = await import_service.commit(
        db=db, spec=WIR_TYPE_IMPORT, user=request.user, obj=obj, background_tasks=background_tasks
    )
    return response_base.success(data=data)


@router.get(
    '/import/template',
    summary='下载 WIR 记录导入模板',
    dependencies=[Depends(RequestPermission('wir:import')), DependsRBAC],
)
async def download_wir_import_template(db: CurrentSession) -> Response:
    raw, name = await import_service.template(db=db, spec=WIR_RECORD_IMPORT)
    return xlsx_attachment(raw, name)


@router.post(
    '/import/preview',
    summary='预览 WIR 记录导入',
    dependencies=[Depends(RequestPermission('wir:import')), DependsRBAC],
)
async def preview_wir_import(
    request: Request,
    db: CurrentSession,
    file: Annotated[UploadFile, File(description='xlsx 文件')],
    mode: Annotated[ImportModeParam, Query(description='导入模式（create：只新增、upsert：新增并更新）')] = 'create',
) -> ResponseSchemaModel[ImportPreviewDetail]:
    raw = await read_table_upload(file)
    data = await import_service.preview(db=db, spec=WIR_RECORD_IMPORT, raw=raw, user=request.user, mode=mode)
    return response_base.success(data=data)


@router.post(
    '/import/commit',
    summary='提交 WIR 记录导入',
    dependencies=[Depends(RequestPermission('wir:import')), DependsRBAC],
)
async def commit_wir_import(
    request: Request, db: CurrentSession, background_tasks: BackgroundTasks, obj: ImportCommitParam
) -> ResponseSchemaModel[ImportCommitDetail]:
    data = await import_service.commit(
        db=db, spec=WIR_RECORD_IMPORT, user=request.user, obj=obj, background_tasks=background_tasks
    )
    return response_base.success(data=data)


# ── WirType ──────────────────────────────────────────────────────────────────────────


@router.get(
    '/types',
    summary='获取所有 WIR 类型',
    dependencies=[DependsJwtAuth],
)
async def get_wir_types(db: CurrentSession) -> ResponseSchemaModel[list[GetWirTypeDetail]]:
    data = await wir_service.get_type_list(db=db)
    return response_base.success(data=data)


@router.post(
    '/types',
    summary='创建 WIR 类型',
    dependencies=[Depends(RequestPermission('wir:type:add')), DependsRBAC],
)
async def create_wir_type(
    db: CurrentSessionTransaction, obj: CreateWirTypeParam
) -> ResponseSchemaModel[GetWirTypeDetail]:
    wir_type = await wir_service.create_type(db=db, obj=obj)
    return response_base.success(data=GetWirTypeDetail.model_validate(wir_type))


@router.put(
    '/types/{pk}',
    summary='更新 WIR 类型',
    dependencies=[Depends(RequestPermission('wir:type:edit')), DependsRBAC],
)
async def update_wir_type(
    db: CurrentSessionTransaction,
    pk: Annotated[int, Path(description='类型 ID')],
    obj: UpdateWirTypeParam,
) -> ResponseModel:
    count = await wir_service.update_type(db=db, pk=pk, obj=obj)
    if count > 0:
        return response_base.success()
    return response_base.fail()


@router.delete(
    '/types/{pk}',
    summary='删除 WIR 类型',
    dependencies=[Depends(RequestPermission('wir:type:del')), DependsRBAC],
)
async def delete_wir_type(
    db: CurrentSessionTransaction, pk: Annotated[int, Path(description='类型 ID')]
) -> ResponseModel:
    count = await wir_service.delete_type(db=db, pk=pk)
    if count > 0:
        return response_base.success()
    return response_base.fail()


# ── WirRecord ────────────────────────────────────────────────────────────────────────


@router.get(
    '',
    summary='分页获取 WIR 台账记录',
    dependencies=[Depends(RequestPermission('wir:record:list')), DependsRBAC, DependsPagination],
)
async def get_wir_records(
    db: CurrentSession,
    dc: Annotated[str | None, Query(description='所属 DC')] = None,
    discipline: Annotated[str | None, Query(description='专业')] = None,
    doc_status: Annotated[str | None, Query(description='批复状态')] = None,
    type_id: Annotated[int | None, Query(description='类型 ID')] = None,
    search: Annotated[str | None, Query(description='搜索（描述 / 别称 / 编号）')] = None,
) -> ResponseSchemaModel[PageData[GetWirRecordDetail]]:
    page_data = await wir_service.get_record_list(
        db=db, dc=dc, discipline=discipline, doc_status=doc_status, type_id=type_id, search=search
    )
    return response_base.success(data=page_data)


@router.get(
    '/{pk}',
    summary='获取单条 WIR 记录详情',
    dependencies=[Depends(RequestPermission('wir:record:list')), DependsRBAC],
)
async def get_wir_record(
    db: CurrentSession, pk: Annotated[int, Path(description='WIR 记录 ID')]
) -> ResponseSchemaModel[GetWirRecordDetail]:
    data = await wir_service.get_record(db=db, pk=pk)
    return response_base.success(data=data)


@router.post(
    '',
    summary='创建 WIR 台账记录',
    dependencies=[Depends(RequestPermission('wir:record:add')), DependsRBAC],
)
async def create_wir_record(
    db: CurrentSessionTransaction, obj: CreateWirRecordParam
) -> ResponseSchemaModel[GetWirRecordDetail]:
    record = await wir_service.create_record(db=db, obj=obj)
    return response_base.success(data=GetWirRecordDetail.model_validate(record))


@router.put(
    '/{pk}',
    summary='更新 WIR 台账记录',
    dependencies=[Depends(RequestPermission('wir:record:edit')), DependsRBAC],
)
async def update_wir_record(
    db: CurrentSessionTransaction,
    pk: Annotated[int, Path(description='WIR 记录 ID')],
    obj: UpdateWirRecordParam,
) -> ResponseModel:
    count = await wir_service.update_record(db=db, pk=pk, obj=obj)
    if count > 0:
        return response_base.success()
    return response_base.fail()


@router.delete(
    '',
    summary='批量删除 WIR 台账记录',
    dependencies=[Depends(RequestPermission('wir:record:del')), DependsRBAC],
)
async def delete_wir_records(db: CurrentSessionTransaction, obj: DeleteWirRecordParam) -> ResponseModel:
    count = await wir_service.delete_records(db=db, obj=obj)
    if count > 0:
        return response_base.success()
    return response_base.fail()
