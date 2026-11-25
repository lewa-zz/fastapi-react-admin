"""wir 导出菜单

Revision ID: wir000000export
Revises: pm000000materialsio
Create Date: 2026-11-25 20:55:00.000000+08:00

给已有的库补一个 WIR 台账的「导出」按钮 —— 种子 SQL 只对 `fba init` 新建的库生效，
升级上来的库不会跟上（见 `backend/utils/data_migration.py` 开头）。

`autogenerate` 对这条是**空的**（没有模型变更），而且 `alembic/env.py` 的
`process_revision_directives` 对空迁移**直接不生成文件**（实测：`db:revision` 只打印
一句「No changes in model detected」，目录里一份新文件都没有）。所以这条和
`pm000000materialsio` 一样手写：`upgrade()` 里不是 DDL 而是幂等的 `add_menu`，
ID 照抄 `plugin/wir/sql/*/init_snowflake.sql` —— 两条路（新建 / 升级）才会收敛到同一份数据。

⚠️ 父级按 `PluginWir` 这个 `name` 解析：WIR 插件没装 / 被卸载时它不存在，`add_menu`
直接跳过（不插孤儿行，否则 `traversal_to_tree` 会把它提到侧边栏根上）。

权限码 `wir:export` 和 `POST /api/v1/sys/wir/export` 上的 `RequestPermission` 一一对应 ——
少一条的表现是非超管永远 403，而界面上只是「按钮点了没反应」。
"""

from alembic import op

from backend.utils.data_migration import add_menu, delete_by_key, seeded_pk_mode

# revision identifiers, used by Alembic.
revision = 'wir000000export'
down_revision = 'pm000000materialsio'
branch_labels = None
depends_on = None

#: 新增的「导出」按钮，和插件种子 SQL 同一套 ID。
#: WIR 的按钮占到 `…000109`（导入），`…000110` 是顶层「项目管理」目录（共用的，不能占），
#: 所以顺延到 `…000111`；材料的区间从 `…000201` 起，撞不上
_WIR_EXPORT_MENU = (2049629108299000111, 'ExportWirRecord', '导出', None, None, 2, 'wir:export', 8, 0, 'PluginWir')


def upgrade() -> None:
    if not seeded_pk_mode():
        return  # 自增主键模式没有基础种子，也就没有菜单要补（同 WIR / PM 那几条迁移）
    menu_id, name, title, path, icon, menu_type, perms, sort, display, parent = _WIR_EXPORT_MENU
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
    if not seeded_pk_mode():
        return
    delete_by_key(op.get_bind(), 'sys_menu', name=_WIR_EXPORT_MENU[1])
