from datetime import datetime

from pydantic import ConfigDict, Field

from backend.app.crm.model import Customer
from backend.common.enums import StatusType
from backend.common.schema import ColumnLengthChecked, SchemaBase


class CustomerSchemaBase(SchemaBase):
    """客户基础模型"""

    name: str = Field(description='客户名称')
    phone: str | None = Field(None, description='联系电话')
    level: int = Field(0, ge=0, le=2, description='客户等级（0：普通、1：重要、2：VIP）')
    status: StatusType = Field(StatusType.enable, description='状态（0：停用、1：正常）')
    remark: str | None = Field(None, description='备注')


class CreateCustomerParam(ColumnLengthChecked, CustomerSchemaBase):
    """创建客户参数"""

    __sa_model__ = Customer

    dept_id: int | None = Field(None, description='所属部门 ID（不传 = 创建人的部门）')
    owner_id: int | None = Field(None, description='负责人用户 ID（不传 = 创建人）')


class UpdateCustomerParam(ColumnLengthChecked, CustomerSchemaBase):
    """更新客户参数"""

    __sa_model__ = Customer

    dept_id: int | None = Field(None, description='所属部门 ID')
    owner_id: int | None = Field(None, description='负责人用户 ID')


class DeleteCustomerParam(SchemaBase):
    """删除客户参数"""

    pks: list[int] = Field(description='客户 ID 列表')


class GetCustomerDetail(CustomerSchemaBase):
    """客户详情"""

    model_config = ConfigDict(from_attributes=True)

    id: int = Field(description='客户 ID')
    dept_id: int | None = Field(None, description='所属部门 ID')
    owner_id: int | None = Field(None, description='负责人用户 ID')
    created_by: int = Field(description='创建者用户 ID')
    created_time: datetime = Field(description='创建时间')
    updated_time: datetime | None = Field(None, description='更新时间')
