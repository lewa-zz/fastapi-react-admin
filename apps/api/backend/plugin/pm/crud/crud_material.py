from sqlalchemy import Select, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.common.security.data_scope import DataScopedCRUD
from backend.plugin.pm.model.material import PmMaterial
from backend.plugin.pm.schema.material import CreatePmMaterialParam, UpdatePmMaterialParam
from backend.utils.timezone import timezone


class CRUDPmMaterial(DataScopedCRUD[PmMaterial]):
    #: 显式豁免数据权限 —— 材料是**项目级共享主数据**，表里没有部门 / 归属人维度。
    #: 继承默认值（过滤）只有 fail-closed 一种效果：受限用户看到 0 条，而材料是
    #: 全项目共用的候选清单（同 `CRUDWirRecord` / `CRUDDictData` 的失败方式）。
    data_scope_enabled = False

    async def get(self, db: AsyncSession, pk: int) -> PmMaterial | None:
        return await self.select_model(db, pk, deleted=0)

    async def get_select(
        self,
        *,
        kind: str | None = None,
        category: str | None = None,
        brand: str | None = None,
        active: bool | None = None,
        search: str | None = None,
    ) -> Select:
        filters = {'deleted': 0}
        if kind is not None:
            filters['kind'] = kind
        if category is not None:
            filters['category'] = category
        if brand is not None:
            filters['brand'] = brand
        if active is not None:
            filters['active'] = active
        # SQL Server 的 OFFSET/FETCH 强制要求 ORDER BY，所以排序写在 CRUD 里而不是接口层
        stmt = await self.select_order('id', 'asc', **filters)
        if search is not None:
            pattern = f'%{search}%'
            stmt = stmt.where(
                (PmMaterial.name_cn.ilike(pattern))
                | (PmMaterial.name_en.ilike(pattern))
                | (PmMaterial.model.ilike(pattern))
                | (PmMaterial.spec.ilike(pattern))
            )
        return stmt

    async def get_by_source_id(self, db: AsyncSession, source_id: int) -> PmMaterial | None:
        return await db.scalar(select(PmMaterial).where(PmMaterial.source_id == source_id, PmMaterial.deleted == 0))

    async def create(self, db: AsyncSession, obj: CreatePmMaterialParam) -> PmMaterial:
        return await self.create_model(db, obj, flush=True)

    async def update(self, db: AsyncSession, pk: int, obj: UpdatePmMaterialParam) -> int:
        data = obj.model_dump(exclude_unset=True)
        return await self.update_model_by_column(db, data, id=pk, deleted=0)

    async def delete(self, db: AsyncSession, pks: list[int]) -> int:
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


pm_material_dao = CRUDPmMaterial(PmMaterial)
