"""项目管理菜单与 wir 台账归属

Revision ID: 4f7c2a91d3e8
Revises: 863c8aab994c
Create Date: 2026-11-24 11:00:00.000000+08:00

把 WIR 台账从「系统管理」里挪出来，挂到新的顶层目录「项目管理」下 ——
和「客户关系」同一个层级，系统管理不再混着业务台账。

只动数据，不动 schema：

- 补一条顶层目录菜单 `Project`（`type=0`，`path=/project`）
- `PluginWir` 的 `path` 改成 `/project/wir`、`parent_id` 指向 `Project`

⚠️ 两处业务键判存在，不硬编码「父级 ID 是哪个」：菜单 ID 在三个方言的种子里
是同一套，但**生产库的 ID 只在生产库里成立**（同 `data_migration` 的三条纪律）。
"""

import sqlalchemy as sa

from alembic import op
from sqlalchemy.engine import Connection

from backend.utils.data_migration import add_menu, delete_by_key, scalar, seeded_pk_mode
from backend.utils.timezone import timezone

# revision identifiers, used by Alembic.
revision = '4f7c2a91d3e8'
down_revision = '863c8aab994c'
branch_labels = None
depends_on = None

#: 顶层「项目管理」目录 —— ID 照抄插件种子 `plugin/wir/sql/*/init_snowflake.sql`
_PROJECT_MENU_ID = 2049629108299000110
_PROJECT_NAME = 'Project'
_PROJECT_PATH = '/project'
#: 和「系统管理」(1) 挨着、排在「日志管理」(3) 前面。顶层现有 0/1/3/4/5/6
_PROJECT_SORT = 2

#: WIR 台账菜单（种子里的业务键是 name，不是 ID）
_WIR_NAME = 'PluginWir'
_WIR_NEW_PATH = '/project/wir'
_WIR_OLD_PATH = '/plugins/wir'
_WIR_NEW_SORT = 1


def _sys_menu(*columns: str) -> sa.TableClause:
    """只带这次真正会碰到的列 —— 迁移要跑在「当时那个 schema」上，别 import 模型"""
    return sa.table('sys_menu', *[sa.column(c) for c in columns])


def _move_wir(conn: Connection, *, parent_name: str | None, path: str, sort: int) -> None:
    """把 WIR 台账挪到指定父级 / 路径

    🔴 `where` 必须带 `deleted == 0`：`deleted` 不是布尔而是「0 或这一行自己的 id」，
    不带它就可能改到一条已软删的菜单 —— 表现为侧边栏凭空多 / 少一条，而且不报错。
    """
    parent_id = scalar(conn, 'sys_menu', 'id', name=parent_name) if parent_name else None
    t = _sys_menu('name', 'path', 'sort', 'parent_id', 'updated_time', 'deleted')
    conn.execute(
        sa
        .update(t)
        .where(t.c.name == _WIR_NAME, t.c.deleted == 0)
        .values(path=path, sort=sort, parent_id=parent_id, updated_time=timezone.now())
    )


def upgrade() -> None:
    if not seeded_pk_mode():
        return  # 自增主键模式没有基础种子，也就没有菜单要补（同 `data_migration` 的口径）

    conn = op.get_bind()
    # 插件没装（或者被卸载了）时 `PluginWir` 不存在：只补顶层目录没有意义，
    # 而且会给一个空目录留在侧边栏上
    if scalar(conn, 'sys_menu', 'id', name=_WIR_NAME) is None:
        return

    add_menu(
        conn,
        menu_id=_PROJECT_MENU_ID,
        name=_PROJECT_NAME,
        title='项目管理',
        path=_PROJECT_PATH,
        icon='fe:folder',
        menu_type=0,
        sort=_PROJECT_SORT,
        display=1,
    )
    _move_wir(conn, parent_name=_PROJECT_NAME, path=_WIR_NEW_PATH, sort=_WIR_NEW_SORT)


def downgrade() -> None:
    if not seeded_pk_mode():
        return

    conn = op.get_bind()
    if scalar(conn, 'sys_menu', 'id', name=_WIR_NAME) is None:
        return

    # 回到「系统管理」下，路径也退回原来的
    _move_wir(conn, parent_name='System', path=_WIR_OLD_PATH, sort=12)
    delete_by_key(conn, 'sys_menu', name=_PROJECT_NAME)
