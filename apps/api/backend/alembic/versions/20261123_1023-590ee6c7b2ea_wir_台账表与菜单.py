"""WIR 台账表与菜单

Revision ID: 590ee6c7b2ea
Revises: f993442e3532
Create Date: 2026-11-23 10:23:21.394078+08:00

"""

import sqlalchemy as sa

from alembic import op

import backend.common.model

from backend.utils.data_migration import add_menu, delete_by_key, seeded_pk_mode

# revision identifiers, used by Alembic.
revision = '590ee6c7b2ea'
down_revision = 'f993442e3532'
branch_labels = None
depends_on = None

#: 和插件种子 SQL 里同一套 ID：`fba init` 新建的库走 `init_snowflake.sql`，
#: 升级上来的库走这里，两条路收敛到同一份数据。
#: (menu_id, name, title, path, icon, menu_type, perms, sort, display, parent_name)
_MENUS = [
    (2049629108299000101, 'PluginWir', 'WIR 台账', '/plugins/wir', 'fe:book-open', 1, None, 12, 1, 'System'),
    (2049629108299000102, 'QueryWir', '查询', None, None, 2, 'wir:record:list', 0, 0, 'PluginWir'),
    (2049629108299000103, 'AddWir', '新增', None, None, 2, 'wir:record:add', 1, 0, 'PluginWir'),
    (2049629108299000104, 'EditWir', '修改', None, None, 2, 'wir:record:edit', 2, 0, 'PluginWir'),
    (2049629108299000105, 'DeleteWir', '删除', None, None, 2, 'wir:record:del', 3, 0, 'PluginWir'),
    (2049629108299000106, 'AddWirType', '新增类型', None, None, 2, 'wir:type:add', 4, 0, 'PluginWir'),
    (2049629108299000107, 'EditWirType', '修改类型', None, None, 2, 'wir:type:edit', 5, 0, 'PluginWir'),
    (2049629108299000108, 'DeleteWirType', '删除类型', None, None, 2, 'wir:type:del', 6, 0, 'PluginWir'),
]


def upgrade() -> None:
    op.create_table(
        'wir_type',
        sa.Column('id', sa.BigInteger(), autoincrement=False, nullable=False, comment='雪花算法主键 ID'),
        sa.Column('type_cn', backend.common.model.UniversalStr(length=128), nullable=False, comment='类型中文名'),
        sa.Column('type_en', backend.common.model.UniversalStr(length=256), nullable=False, comment='类型英文名'),
        sa.Column('created_time', backend.common.model.TimeZone(timezone=True), nullable=False, comment='创建时间'),
        sa.Column('updated_time', backend.common.model.TimeZone(timezone=True), nullable=True, comment='更新时间'),
        sa.Column(
            'deleted', sa.BigInteger(), server_default='0', nullable=False, comment='是否已删除（0：否；id：是）'
        ),
        sa.Column('deleted_time', backend.common.model.TimeZone(timezone=True), nullable=True, comment='删除时间'),
        sa.PrimaryKeyConstraint('id'),
        comment='WIR 类型参考表（中英对照）',
    )
    op.create_index(op.f('ix_wir_type_id'), 'wir_type', ['id'], unique=True)
    op.create_table(
        'wir_record',
        sa.Column('id', sa.BigInteger(), autoincrement=False, nullable=False, comment='雪花算法主键 ID'),
        sa.Column(
            'from_party', backend.common.model.UniversalStr(length=64), nullable=True, comment='提交方（如 DRT）'
        ),
        sa.Column(
            'tml_no',
            backend.common.model.UniversalStr(length=128),
            nullable=True,
            comment='TML 申请编号（进 PMWeb 之前）',
        ),
        sa.Column(
            'pmweb_no',
            backend.common.model.UniversalStr(length=256),
            nullable=True,
            comment='PMWeb 正式编号（顾问系统号）',
        ),
        sa.Column(
            'doc_type', backend.common.model.UniversalStr(length=16), nullable=True, comment='文件类型（WIR / MIR）'
        ),
        sa.Column(
            'discipline', backend.common.model.UniversalStr(length=16), nullable=True, comment='专业（BMS / SEC / ELV）'
        ),
        sa.Column('description', backend.common.model.UniversalText(), nullable=True, comment='检查内容描述'),
        sa.Column('drt_submitted', backend.common.model.TimeZone(timezone=True), nullable=True, comment='DRT 提交日期'),
        sa.Column('pmx_submitted', backend.common.model.TimeZone(timezone=True), nullable=True, comment='PMX 提交日期'),
        sa.Column(
            'cb_inspection', backend.common.model.TimeZone(timezone=True), nullable=True, comment='C&B 顾问检查日期'
        ),
        sa.Column(
            'doc_status',
            backend.common.model.UniversalStr(length=64),
            nullable=True,
            comment='文件批复状态（Approved / Approved as Noted）',
        ),
        sa.Column('comment', backend.common.model.UniversalText(), nullable=True, comment='顾问意见'),
        sa.Column(
            'another_desc', backend.common.model.UniversalStr(length=512), nullable=True, comment='别称/中文描述'
        ),
        sa.Column(
            'dc',
            backend.common.model.UniversalStr(length=32),
            nullable=True,
            comment='所属 DC（DC1-Fitout / DC2-Fitout / DC3-Fitout）',
        ),
        sa.Column(
            'filepath',
            backend.common.model.UniversalStr(length=1024),
            nullable=True,
            comment='签字件路径（文件名 → 目录）',
        ),
        sa.Column('type_id', sa.BigInteger(), nullable=True, comment='WIR 类型 ID'),
        sa.Column('created_time', backend.common.model.TimeZone(timezone=True), nullable=False, comment='创建时间'),
        sa.Column('updated_time', backend.common.model.TimeZone(timezone=True), nullable=True, comment='更新时间'),
        sa.Column(
            'deleted', sa.BigInteger(), server_default='0', nullable=False, comment='是否已删除（0：否；id：是）'
        ),
        sa.Column('deleted_time', backend.common.model.TimeZone(timezone=True), nullable=True, comment='删除时间'),
        sa.ForeignKeyConstraint(['type_id'], ['wir_type.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
        comment='WIR 台账主表',
    )
    # `tml_no` 可空，SQL Server 的 UNIQUE 约束认为多个 NULL 相等 —— 那里改用
    # 只对非 NULL 生效的筛选唯一索引（同 `app/admin/model/user.py` 的 `_EMAIL_UNIQUE`）。
    if op.get_bind().dialect.name == 'mssql':
        op.create_index(
            'uk_wir_record_tml_no_deleted',
            'wir_record',
            ['tml_no', 'deleted'],
            unique=True,
            mssql_where=sa.text('tml_no IS NOT NULL'),
        )
    else:
        op.create_unique_constraint('uk_wir_record_tml_no_deleted', 'wir_record', ['tml_no', 'deleted'])
    op.create_index(op.f('ix_wir_record_dc'), 'wir_record', ['dc'], unique=False)
    op.create_index(op.f('ix_wir_record_discipline'), 'wir_record', ['discipline'], unique=False)
    op.create_index(op.f('ix_wir_record_doc_status'), 'wir_record', ['doc_status'], unique=False)
    op.create_index(op.f('ix_wir_record_id'), 'wir_record', ['id'], unique=True)
    op.create_index(op.f('ix_wir_record_pmweb_no'), 'wir_record', ['pmweb_no'], unique=False)
    op.create_index(op.f('ix_wir_record_tml_no'), 'wir_record', ['tml_no'], unique=False)

    if not seeded_pk_mode():
        return  # 自增主键模式没有基础种子，也就没有菜单要补
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
        # 倒序删：先按钮后目录，否则子项变孤儿被提到侧边栏根上
        for menu in reversed(_MENUS):
            delete_by_key(conn, 'sys_menu', name=menu[1])

    op.drop_index(op.f('ix_wir_record_tml_no'), table_name='wir_record')
    op.drop_index(op.f('ix_wir_record_pmweb_no'), table_name='wir_record')
    op.drop_index(op.f('ix_wir_record_id'), table_name='wir_record')
    op.drop_index(op.f('ix_wir_record_doc_status'), table_name='wir_record')
    op.drop_index(op.f('ix_wir_record_discipline'), table_name='wir_record')
    op.drop_index(op.f('ix_wir_record_dc'), table_name='wir_record')
    if op.get_bind().dialect.name == 'mssql':
        op.drop_index('uk_wir_record_tml_no_deleted', table_name='wir_record')
    else:
        op.drop_constraint('uk_wir_record_tml_no_deleted', 'wir_record', type_='unique')
    op.drop_table('wir_record')
    op.drop_index(op.f('ix_wir_type_id'), table_name='wir_type')
    op.drop_table('wir_type')
