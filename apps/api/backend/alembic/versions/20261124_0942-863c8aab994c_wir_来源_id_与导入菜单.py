"""wir 来源 id 与导入菜单

Revision ID: 863c8aab994c
Revises: 590ee6c7b2ea
Create Date: 2026-11-24 09:42:31.040808+08:00

"""

import sqlalchemy as sa

from alembic import op

from backend.utils.data_migration import add_menu, delete_by_key, seeded_pk_mode

# revision identifiers, used by Alembic.
revision = '863c8aab994c'
down_revision = '590ee6c7b2ea'
branch_labels = None
depends_on = None

#: 新增的「导入」按钮，和插件种子 SQL 同一套 ID
_WIR_IMPORT_MENU = (2049629108299000109, 'ImportWir', '导入', None, None, 2, 'wir:import', 7, 0, 'PluginWir')


def upgrade() -> None:
    op.add_column(
        'wir_record',
        sa.Column('source_id', sa.BigInteger(), nullable=True, comment='来源 Excel 行 ID（导入幂等键）'),
    )
    op.create_index(op.f('ix_wir_record_source_id'), 'wir_record', ['source_id'], unique=False)

    if not seeded_pk_mode():
        return  # 自增主键模式没有基础种子，也就没有菜单要补
    menu_id, name, title, path, icon, menu_type, perms, sort, display, parent = _WIR_IMPORT_MENU
    add_menu(
        op.get_bind(),
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
        delete_by_key(op.get_bind(), 'sys_menu', name=_WIR_IMPORT_MENU[1])

    op.drop_index(op.f('ix_wir_record_source_id'), table_name='wir_record')
    op.drop_column('wir_record', 'source_id')
