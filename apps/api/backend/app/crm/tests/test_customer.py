"""客户管理：接口走一遍 CRUD，再验受限用户碰不到范围外的客户"""

import asyncio

from types import SimpleNamespace

import pytest

from starlette.testclient import TestClient

from backend.app.crm.schema.customer import DeleteCustomerParam, UpdateCustomerParam
from backend.app.crm.service.customer_service import customer_service
from backend.common.exception import errors
from backend.common.security.data_scope import set_current_user
from backend.database.db import (
    create_database_async_engine,
    create_database_async_session,
    get_database_url,
)

BASE = '/crm/customers'


def _restricted() -> SimpleNamespace:
    """开了范围过滤、一条规则都没有 —— fail-closed，什么都看不见"""
    scope = SimpleNamespace(status=1, rules=[])
    return SimpleNamespace(
        is_superuser=False,
        id=1,
        dept_id=1,
        roles=[SimpleNamespace(status=1, is_filter_scopes=True, scopes=[scope])],
    )


def _as_restricted(fn):
    async def go():
        engine = create_database_async_engine(get_database_url(unittest=True))
        try:
            async with create_database_async_session(engine).begin() as db:
                set_current_user(_restricted())
                try:
                    return await fn(db)
                finally:
                    set_current_user(None)
        finally:
            await engine.dispose()

    return asyncio.run(go())


@pytest.fixture
def customer(client: TestClient, token_headers: dict[str, str]):
    name = 'pytest-客户'
    res = client.post(BASE, headers=token_headers, json={'name': name, 'level': 1})
    assert res.json()['code'] == 200, res.text
    items = client.get(BASE, headers=token_headers, params={'name': name}).json()['data']['items']
    assert len(items) == 1
    yield items[0]
    client.request('DELETE', BASE, headers=token_headers, json={'pks': [int(items[0]['id'])]})


def test_crud(client: TestClient, token_headers: dict[str, str], customer: dict) -> None:
    pk = customer['id']
    assert isinstance(pk, str)  # 雪花 ID 下发成字符串（硬纪律 6）
    assert customer['created_by'] == customer['owner_id']  # 不传负责人 = 创建人

    res = client.put(
        f'{BASE}/{pk}',
        headers=token_headers,
        json={'name': 'pytest-客户-改', 'level': 2},
    )
    assert res.json()['code'] == 200, res.text
    detail = client.get(f'{BASE}/{pk}', headers=token_headers).json()['data']
    assert detail['level'] == 2
    assert detail['dept_id'] == customer['dept_id']  # 没传的字段不能被冲成 NULL

    res = client.request('DELETE', BASE, headers=token_headers, json={'pks': [int(pk)]})
    assert res.json()['code'] == 200
    assert client.get(f'{BASE}/{pk}', headers=token_headers).status_code == 404


def test_restricted_user_cannot_touch_rows_outside_scope(
    client: TestClient, token_headers: dict[str, str], customer: dict
) -> None:
    pk = int(customer['id'])

    with pytest.raises(errors.NotFoundError):
        _as_restricted(lambda db: customer_service.update(db=db, pk=pk, obj=UpdateCustomerParam(name='越权')))
    assert _as_restricted(lambda db: customer_service.delete(db=db, obj=DeleteCustomerParam(pks=[pk]))) == 0

    # 超管视角：那一行还在、名字没被改
    assert client.get(f'{BASE}/{pk}', headers=token_headers).json()['data']['name'] == 'pytest-客户'
