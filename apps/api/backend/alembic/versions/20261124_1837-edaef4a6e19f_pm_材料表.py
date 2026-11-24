"""pm 材料表与菜单

Revision ID: edaef4a6e19f
Revises: 4f7c2a91d3e8
Create Date: 2026-11-24 18:37:41.647684+08:00

PM 材料主数据（`pm_material`）+ 5 条菜单。

菜单挂在**已存在的**顶层目录「项目管理」（`Project`，`/project`）下 —— 那条目录由
WIR 插件的种子 / 迁移建的，两个插件共用。所以：

- 这里先 `add_menu(Project)` 再挂自己的 5 条：`insert_if_absent` 按 `name` 幂等，
  WIR 已装时是 no-op；WIR 没装时侧边栏才有父级
- `downgrade` **只删自己那 5 条**，不删 `Project`（WIR 还在用）

⚠️ `source_id` 可空，SQL Server 的 UNIQUE 约束认为多个 NULL 彼此相等 —— 那里改用
只对非 NULL 生效的筛选唯一索引（同 `plugin/wir` 的 `_TML_NO_UNIQUE`）。
"""

import sqlalchemy as sa

from alembic import op

import backend.common.model

from backend.utils.data_migration import add_menu, delete_by_key, seeded_pk_mode

# revision identifiers, used by Alembic.
revision = 'edaef4a6e19f'
down_revision = '4f7c2a91d3e8'
branch_labels = None
depends_on = None

#: 顶层「项目管理」目录 —— ID 照抄 `plugin/wir/sql/*/init_snowflake.sql`
_PROJECT_MENU = (2049629108299000110, 'Project', '项目管理', '/project', 'fe:folder', 0, None, 2, 1, None)

#: 和插件种子 SQL 里同一套 ID：`fba init` 新建的库走 `init_snowflake.sql`，
#: 升级上来的库走这里，两条路收敛到同一份数据。
#: (menu_id, name, title, path, icon, menu_type, perms, sort, display, parent_name)
_MENUS = [
    _PROJECT_MENU,
    (2049629108299000201, 'PluginPmMaterial', '材料', '/project/pm/materials', 'fe:box', 1, None, 2, 1, 'Project'),
    (2049629108299000202, 'QueryPmMaterial', '查询', None, None, 2, 'pm:material:list', 0, 0, 'PluginPmMaterial'),
    (2049629108299000203, 'AddPmMaterial', '新增', None, None, 2, 'pm:material:add', 1, 0, 'PluginPmMaterial'),
    (2049629108299000204, 'EditPmMaterial', '修改', None, None, 2, 'pm:material:edit', 2, 0, 'PluginPmMaterial'),
    (2049629108299000205, 'DeletePmMaterial', '删除', None, None, 2, 'pm:material:del', 3, 0, 'PluginPmMaterial'),
]

#: `downgrade` 只删本插件自己的菜单 —— `Project` 是 WIR 建的和它共用的
_OWN_MENUS = _MENUS[1:]


def _has_table() -> bool:
    """表已经在了吗

    ⚠️ 开发环境的 lifespan 会对当前模型跑 `create_all` —— 模型先落地、之后才跑这条迁移的
    库里，`pm_material` 已经是目标结构了。无条件 `create_table` 会当场 `DuplicateTable`，
    而那种库和「刚从迁移升上来的库」在结构上没有区别。
    同 `c0000000comments` 的 `_has_column()`：这类「补历史遗留」的步骤必须幂等。
    新建的库（`fba init`）走 `create_all` + `stamp head`，根本不会执行到这里。
    """
    return sa.inspect(op.get_bind()).has_table('pm_material')


def _create_table() -> None:
    op.create_table(
        'pm_material',
        sa.Column('id', sa.BigInteger(), autoincrement=False, nullable=False, comment='雪花算法主键 ID'),
        sa.Column(
            'kind',
            backend.common.model.UniversalStr(length=64),
            nullable=False,
            comment='类型（PLC / Program（编程/软件）…）',
        ),
        sa.Column(
            'category', backend.common.model.UniversalStr(length=64), nullable=False, comment='类别（BMS控制柜 …）'
        ),
        sa.Column('name_cn', backend.common.model.UniversalStr(length=128), nullable=False, comment='材料中文名'),
        sa.Column('name_en', backend.common.model.UniversalStr(length=256), nullable=False, comment='材料英文名'),
        sa.Column(
            'unit', backend.common.model.UniversalStr(length=32), nullable=False, comment='单位（台/件、套、米…）'
        ),
        sa.Column('source_id', sa.BigInteger(), nullable=True, comment='来源 Excel 行 ID（导入幂等键）'),
        sa.Column('model', backend.common.model.UniversalStr(length=64), nullable=True, comment='型号'),
        sa.Column('spec', backend.common.model.UniversalText(), nullable=True, comment='规格描述（含换行）'),
        sa.Column('brand', backend.common.model.UniversalStr(length=64), nullable=True, comment='品牌'),
        sa.Column('qty', sa.Numeric(precision=14, scale=4), nullable=True, comment='合同数量'),
        sa.Column('price', sa.Numeric(precision=14, scale=4), nullable=True, comment='合同单价'),
        sa.Column('contract_price', sa.Numeric(precision=14, scale=4), nullable=True, comment='合同合价'),
        sa.Column('in_price', sa.Numeric(precision=14, scale=4), nullable=True, comment='报入单价'),
        sa.Column('out_price', sa.Numeric(precision=14, scale=4), nullable=True, comment='报出价'),
        sa.Column('market_price', sa.Numeric(precision=14, scale=4), nullable=True, comment='市场价'),
        sa.Column('memo', backend.common.model.UniversalStr(length=256), nullable=True, comment='备注'),
        sa.Column('source', backend.common.model.UniversalStr(length=128), nullable=True, comment='来源'),
        sa.Column('currency', backend.common.model.UniversalStr(length=8), nullable=False, comment='币种'),
        sa.Column('active', sa.Boolean(), nullable=False, comment='是否启用（停用不出现在候选里）'),
        sa.Column('created_time', backend.common.model.TimeZone(timezone=True), nullable=False, comment='创建时间'),
        sa.Column('updated_time', backend.common.model.TimeZone(timezone=True), nullable=True, comment='更新时间'),
        sa.Column(
            'deleted', sa.BigInteger(), server_default='0', nullable=False, comment='是否已删除（0：否；id：是）'
        ),
        sa.Column('deleted_time', backend.common.model.TimeZone(timezone=True), nullable=True, comment='删除时间'),
        sa.PrimaryKeyConstraint('id'),
        comment='BKK03 材料主数据',
    )
    # `source_id` 可空，SQL Server 的 UNIQUE 约束认为多个 NULL 相等 —— 那里改用
    # 只对非 NULL 生效的筛选唯一索引（同 `plugin/wir` 的 `uk_wir_record_tml_no_deleted`）
    if op.get_bind().dialect.name == 'mssql':
        op.create_index(
            'uk_pm_material_source_id_deleted',
            'pm_material',
            ['source_id', 'deleted'],
            unique=True,
            mssql_where=sa.text('source_id IS NOT NULL'),
        )
    else:
        op.create_unique_constraint('uk_pm_material_source_id_deleted', 'pm_material', ['source_id', 'deleted'])
    op.create_index('ix_pm_material_brand', 'pm_material', ['brand'], unique=False)
    op.create_index('ix_pm_material_category_active', 'pm_material', ['category', 'active'], unique=False)
    op.create_index(op.f('ix_pm_material_id'), 'pm_material', ['id'], unique=True)
    op.create_index('ix_pm_material_kind', 'pm_material', ['kind'], unique=False)
    op.create_index('ix_pm_material_name_cn', 'pm_material', ['name_cn'], unique=False)


def _drop_table() -> None:
    op.drop_index('ix_pm_material_name_cn', table_name='pm_material')
    op.drop_index('ix_pm_material_kind', table_name='pm_material')
    op.drop_index(op.f('ix_pm_material_id'), table_name='pm_material')
    op.drop_index('ix_pm_material_category_active', table_name='pm_material')
    op.drop_index('ix_pm_material_brand', table_name='pm_material')
    if op.get_bind().dialect.name == 'mssql':
        op.drop_index('uk_pm_material_source_id_deleted', table_name='pm_material')
    else:
        op.drop_constraint('uk_pm_material_source_id_deleted', 'pm_material', type_='unique')
    op.drop_table('pm_material')


def upgrade() -> None:
    if not _has_table():
        _create_table()

    if not seeded_pk_mode():
        return  # 自增主键模式没有基础种子，也就没有菜单要补（同 WIR 那条迁移）
    conn = op.get_bind()
    for (
        menu_id,
        name,
        title,
        path,
        icon,
        menu_type,
        perms,
        sort,
        display,
        parent,
    ) in _MENUS:
        add_menu(
            conn,
            menu_id=menu_id,
            name=name,
            title=title,
            path=path,
            perms=perms,
            icon=icon,
            menu_type=menu_type,
            sort=sort,
            display=display,
            parent_name=parent,
        )


def downgrade() -> None:
    if seeded_pk_mode():
        conn = op.get_bind()
        # 倒序删：先按钮后页面，否则子项变孤儿被提到侧边栏根上。
        # `Project` 刻意不删 —— 它是 WIR 建的和本插件共用的顶层目录
        for menu in reversed(_OWN_MENUS):
            delete_by_key(conn, 'sys_menu', name=menu[1])

    if _has_table():
        _drop_table()
