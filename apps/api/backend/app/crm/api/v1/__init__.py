from fastapi import APIRouter

from backend.app.crm.api.v1.customer import router as customer_router

router = APIRouter(prefix='/crm')

router.include_router(customer_router, prefix='/customers', tags=['客户管理'])
