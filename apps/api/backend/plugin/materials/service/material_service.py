from sqlalchemy.ext.asyncio import AsyncSession

from backend.common.exception import errors
from backend.common.i18n import t
from backend.common.pagination import paging_data
from backend.plugin.materials.crud.crud_material import pm_material_dao
from backend.plugin.materials.model.material import PmMaterial
from backend.plugin.materials.schema.material import (
    CreatePmMaterialParam,
    DeletePmMaterialParam,
    GetPmMaterialDetail,
    UpdatePmMaterialParam,
)


class PmService:
    # ── PmMaterial ───────────────────────────────────────────────────────────────

    @staticmethod
    async def get_material(db: AsyncSession, pk: int) -> GetPmMaterialDetail:
        material = await pm_material_dao.get(db, pk)
        if not material:
            raise errors.NotFoundError(msg=t('error.pm.material_not_found', pk=pk))
        return GetPmMaterialDetail.model_validate(material)

    async def get_material_list(
        self,
        db: AsyncSession,
        *,
        kind: str | None = None,
        category: str | None = None,
        brand: str | None = None,
        active: bool | None = None,
        search: str | None = None,
    ) -> dict:
        stmt = await pm_material_dao.get_select(kind=kind, category=category, brand=brand, active=active, search=search)
        return await paging_data(db, stmt)

    async def create_material(self, db: AsyncSession, obj: CreatePmMaterialParam) -> PmMaterial:
        # `source_id` 是导入幂等键：同一份材料表导两次不该多一行。
        # 手工新增可以不传（可空），但传了就必须唯一 —— 撞了报 409 而不是 500
        if obj.source_id is not None:
            existing = await pm_material_dao.get_by_source_id(db, obj.source_id)
            if existing:
                raise errors.ConflictError(msg=t('error.pm.source_id_exists', source_id=obj.source_id))
        return await pm_material_dao.create(db, obj)

    async def update_material(self, db: AsyncSession, pk: int, obj: UpdatePmMaterialParam) -> int:
        material = await pm_material_dao.get(db, pk)
        if not material:
            raise errors.NotFoundError(msg=t('error.pm.material_not_found', pk=pk))
        if obj.source_id is not None and obj.source_id != material.source_id:
            existing = await pm_material_dao.get_by_source_id(db, obj.source_id)
            if existing:
                raise errors.ConflictError(msg=t('error.pm.source_id_exists', source_id=obj.source_id))
        return await pm_material_dao.update(db, pk, obj)

    async def delete_materials(self, db: AsyncSession, obj: DeletePmMaterialParam) -> int:
        return await pm_material_dao.delete(db, obj.pks)


pm_service = PmService()
