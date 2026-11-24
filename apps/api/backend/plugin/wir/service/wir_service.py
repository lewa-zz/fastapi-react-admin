from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.common.exception import errors
from backend.common.i18n import t
from backend.common.pagination import paging_data
from backend.plugin.wir.crud.crud_wir import wir_record_dao, wir_type_dao
from backend.plugin.wir.model.wir import WirRecord, WirType
from backend.plugin.wir.schema.wir import (
    CreateWirRecordParam,
    CreateWirTypeParam,
    DeleteWirRecordParam,
    GetWirRecordDetail,
    GetWirTypeDetail,
    UpdateWirRecordParam,
    UpdateWirTypeParam,
)


async def _with_type_names(db: AsyncSession, items: list[dict]) -> list[dict]:
    """给分页结果补上 `type_cn` / `type_en`（列表只 join 一次，不按行 N+1）

    `paging_data()` 的 items 是 dict（见 `backend/alembic/AGENTS.md`），直接往里面塞键即可。
    """
    type_ids = {item['type_id'] for item in items if item.get('type_id') is not None}
    if not type_ids:
        return items
    rows = (await db.scalars(select(WirType).where(WirType.id.in_(type_ids), WirType.deleted == 0))).all()
    type_map = {row.id: row for row in rows}
    for item in items:
        wir_type = type_map.get(item.get('type_id'))
        item['type_cn'] = wir_type.type_cn if wir_type else None
        item['type_en'] = wir_type.type_en if wir_type else None
    return items


class WirService:
    # ── WirType ──────────────────────────────────────────────────────────────────

    @staticmethod
    async def get_type_list(db: AsyncSession) -> list[GetWirTypeDetail]:
        stmt = await wir_type_dao.get_select()
        result = await db.execute(stmt)
        rows = result.scalars().all()
        return [GetWirTypeDetail.model_validate(row) for row in rows]

    @staticmethod
    async def create_type(db: AsyncSession, obj: CreateWirTypeParam) -> WirType:
        existing = await wir_type_dao.get_by_name(db, obj.type_cn)
        if existing:
            raise errors.ConflictError(msg=t('error.wir.type_exists', type_cn=obj.type_cn))
        return await wir_type_dao.create(db, obj)

    @staticmethod
    async def update_type(db: AsyncSession, pk: int, obj: UpdateWirTypeParam) -> int:
        wir_type = await wir_type_dao.get(db, pk)
        if not wir_type:
            raise errors.NotFoundError(msg=t('error.wir.type_not_found', pk=pk))
        if obj.type_cn and obj.type_cn != wir_type.type_cn:
            existing = await wir_type_dao.get_by_name(db, obj.type_cn)
            if existing:
                raise errors.ConflictError(msg=t('error.wir.type_exists', type_cn=obj.type_cn))
        return await wir_type_dao.update(db, pk, obj)

    @staticmethod
    async def delete_type(db: AsyncSession, pk: int) -> int:
        wir_type = await wir_type_dao.get(db, pk)
        if not wir_type:
            raise errors.NotFoundError(msg=t('error.wir.type_not_found', pk=pk))
        referenced = await db.scalar(
            select(func.count()).select_from(WirRecord).where(WirRecord.type_id == pk, WirRecord.deleted == 0)
        )
        if referenced:
            raise errors.ConflictError(msg=t('error.wir.type_in_use', type_cn=wir_type.type_cn, count=referenced))
        return await wir_type_dao.delete(db, pk)

    # ── WirRecord ────────────────────────────────────────────────────────────────

    async def get_record(self, db: AsyncSession, pk: int) -> GetWirRecordDetail:
        record = await wir_record_dao.get(db, pk)
        if not record:
            raise errors.NotFoundError(msg=t('error.wir.record_not_found', pk=pk))
        detail = GetWirRecordDetail.model_validate(record)
        if record.type_id is not None:
            wir_type = await wir_type_dao.get(db, record.type_id)
            if wir_type:
                detail.type_cn = wir_type.type_cn
                detail.type_en = wir_type.type_en
        return detail

    async def get_record_list(
        self,
        db: AsyncSession,
        dc: str | None = None,
        discipline: str | None = None,
        doc_status: str | None = None,
        type_id: int | None = None,
        search: str | None = None,
    ) -> dict:
        stmt = await wir_record_dao.get_select(
            dc=dc, discipline=discipline, doc_status=doc_status, type_id=type_id, search=search
        )
        page_data = await paging_data(db, stmt)
        page_data['items'] = await _with_type_names(db, page_data['items'])
        return page_data

    async def create_record(self, db: AsyncSession, obj: CreateWirRecordParam) -> WirRecord:
        if obj.tml_no:
            existing = await wir_record_dao.get_by_tml_no(db, obj.tml_no)
            if existing:
                raise errors.ConflictError(msg=t('error.wir.tml_no_exists', tml_no=obj.tml_no))
        return await wir_record_dao.create(db, obj)

    async def update_record(self, db: AsyncSession, pk: int, obj: UpdateWirRecordParam) -> int:
        record = await wir_record_dao.get(db, pk)
        if not record:
            raise errors.NotFoundError(msg=t('error.wir.record_not_found', pk=pk))
        if obj.tml_no and obj.tml_no != record.tml_no:
            existing = await wir_record_dao.get_by_tml_no(db, obj.tml_no)
            if existing:
                raise errors.ConflictError(msg=t('error.wir.tml_no_exists', tml_no=obj.tml_no))
        return await wir_record_dao.update(db, pk, obj)

    async def delete_records(self, db: AsyncSession, obj: DeleteWirRecordParam) -> int:
        return await wir_record_dao.delete(db, obj.pks)


wir_service = WirService()
