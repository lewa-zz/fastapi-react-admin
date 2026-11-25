"""pm 材料导入导出菜单

Revision ID: pm000000materialsio
Revises: edaef4a6e19f
Create Date: 2026-11-25 20:48:00.000000+08:00

给已有的库补两个材料按钮（导入 / 导出）—— 种子 SQL 只对 `fba init` 新建的库生效，
升级上来的库不会跟上（见 `backend/utils/data_migration.py` 开头）。

`autogenerate` 对这条是**空的**（没有模型变更），所以手写；`upgrade()` 里不是 DDL
而是幂等的 `add_menu`，ID 照抄 `plugin/materials/sql/*/init_snowflake.sql` ——
两条路（新建 / 升级）才会收敛到同一份数据。

⚠️ 父级按 `PluginPmMaterial` 这个 `name` 解析：材料插件没装 / 被卸载时它不存在，
`add_menu` 直接跳过（不插孤儿行，否则 `traversal_to_tree` 会把它提到侧边栏根上）。

权限码 `pm:material:import` / `pm:material:export` 和路由上的 `RequestPermission`
一一对应 —— 少一条的表现是非超管永远 403，而界面上只是「按钮点了没反应」。
"""

from alembic import op

from backend.utils.data_migration import add_menu, delete_by_key, seeded_pk_mode

# revision identifiers, used by Alembic.
revision = 'pm000000materialsio'
down_revision = 'edaef4a6e19f'
branch_labels = None
depends_on = None

#: (menu_id, name, title, path, icon, menu_type, perms, sort, display, parent_name)
#: 和插件种子 SQL 同一套 ID：`…000206` 导入、`…000207` 导出（材料页是 `…000201`）
_MENUS = [
    (2049629108299000206, 'ImportPmMaterial', '导入', None, None, 2, 'pm:material:import', 4, 0, 'PluginPmMaterial'),
    (2049629108299000207, 'ExportPmMaterial', '导出', None, None, 2, 'pm:material:export', 5, 0, 'PluginPmMaterial'),
]


def upgrade() -> None:
    if not seeded_pk_mode():
        return  # 自增主键模式没有基础种子，也就没有菜单要补（同 WIR / PM 那两条迁移）
    conn = op.get_bind()
    for menu_id, name, title, path, icon, menu_type, perms, sort, display, parent in _MENUS:
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
    if not seeded_pk_mode():
        return
    conn = op.get_bind()
    for menu in reversed(_MENUS):
        delete_by_key(conn, 'sys_menu', name=menu[1])
