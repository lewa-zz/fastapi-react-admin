from sqlalchemy import Select, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.common.security.data_scope import DataScopedCRUD
from backend.plugin.wir.model.wir import WirRecord, WirType
from backend.plugin.wir.schema.wir import (
    CreateWirRecordParam,
    CreateWirTypeParam,
    UpdateWirRecordParam,
    UpdateWirTypeParam,
)
from backend.utils.timezone import timezone


class CRUDWirType(DataScopedCRUD[WirType]):
    #: 显式豁免数据权限 —— 类型是**全局参考数据**（下拉选项），表里没有部门 / 归属人维度。
    #: 继承默认值（过滤）只有 fail-closed 一种效果：受限用户会在下拉里看不到任何类型
    #: （同 `CRUDNotice` / `CRUDDictData` 的失败方式：界面空白、无任何提示）。
    data_scope_enabled = False

    async def get(self, db: AsyncSession, pk: int) -> WirType | None:
        return await self.select_model(db, pk, deleted=0)

    async def get_select(self) -> Select:
        return await self.select_order('id', 'asc', deleted=0)

    async def get_by_name(self, db: AsyncSession, type_cn: str) -> WirType | None:
        return await db.scalar(select(WirType).where(WirType.type_cn == type_cn, WirType.deleted == 0))

    async def create(self, db: AsyncSession, obj: CreateWirTypeParam) -> WirType:
        return await self.create_model(db, obj, flush=True)

    async def update(self, db: AsyncSession, pk: int, obj: UpdateWirTypeParam) -> int:
        data = obj.model_dump(exclude_unset=True)
        return await self.update_model_by_column(db, data, id=pk, deleted=0)

    async def delete(self, db: AsyncSession, pk: int) -> int:
        return await self.delete_model_by_column(
            db,
            allow_multiple=False,
            logical_deletion=True,
            deleted_flag_column='deleted',
            deleted_flag_value=self.model.id,
            deleted_at_column='deleted_time',
            deleted_at_factory=timezone.now(),
            id=pk,
            deleted=0,
        )


class CRUDWirRecord(DataScopedCRUD[WirRecord]):
    #: 显式豁免数据权限 —— WIR 台账是项目级共享记录（一条 WIR 不归属某个部门 / 人），
    #: 表里没有可过滤维度，过滤只有 fail-closed 一种效果（受限用户看到 0 条）。
    data_scope_enabled = False

    async def get(self, db: AsyncSession, pk: int) -> WirRecord | None:
        return await self.select_model(db, pk, deleted=0)

    async def get_select(
        self,
        dc: str | None = None,
        discipline: str | None = None,
        doc_status: str | None = None,
        type_id: int | None = None,
        search: str | None = None,
    ) -> Select:
        filters = {'deleted': 0}
        if dc is not None:
            filters['dc'] = dc
        if discipline is not None:
            filters['discipline'] = discipline
        if doc_status is not None:
            filters['doc_status'] = doc_status
        if type_id is not None:
            filters['type_id'] = type_id
        stmt = await self.select_order('id', 'asc', **filters)
        if search is not None:
            pattern = f'%{search}%'
            stmt = stmt.where(
                (WirRecord.description.ilike(pattern))
                | (WirRecord.another_desc.ilike(pattern))
                | (WirRecord.tml_no.ilike(pattern))
                | (WirRecord.pmweb_no.ilike(pattern))
            )
        return stmt

    async def get_by_tml_no(self, db: AsyncSession, tml_no: str) -> WirRecord | None:
        return await db.scalar(select(WirRecord).where(WirRecord.tml_no == tml_no, WirRecord.deleted == 0))

    async def create(self, db: AsyncSession, obj: CreateWirRecordParam) -> WirRecord:
        return await self.create_model(db, obj, flush=True)

    async def update(self, db: AsyncSession, pk: int, obj: UpdateWirRecordParam) -> int:
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


wir_type_dao = CRUDWirType(WirType)
wir_record_dao = CRUDWirRecord(WirRecord)
