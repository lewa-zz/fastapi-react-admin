"""PM 插件的种子 / 卸载 SQL：12 份文件齐全、五条菜单、不碰共用的顶层目录。

盯的是两件「少一行 / 多一行都照样跑」的事：

- **某个方言缺一份脚本。** `plugin/sql.py: get_plugin_sql()` 找不到文件就返回 `None` ——
  `fba init` / `fba add materials` 不报错，只是那个库上**一条菜单都不建**，症状是侧边栏里
  没有材料页。`plugin/validator.py` 会拦这种情况，但它只在**装插件**那一刻跑，
  `fba init` 的建库路径走不到它。
- **卸载脚本里混进 `DELETE ... name = 'Project'`。** 顶层「项目管理」目录是 WIR 建的、
  WIR 与 PM 共用；删掉它 WIR 台账的入口一起没了，而 WIR 自己的 destroy 并不重建它。
  更隐蔽的是它**在只装了 PM 的库上是空操作**（那会儿 Project 还不存在），
  所以只有两个插件都装的环境才会出事 —— 也就是真实部署。

⚠️ 表 `pm_material` **不在这里建**：它归 alembic 迁移（`edaef4a6e19f`，由 autogenerate
生成）。插件 SQL 只负责菜单，`destroy` 顺手把表 drop 掉（非 alembic 部署那份契约）。
手写建表 DDL 进这些脚本等于第二条真相源，会跟迁移静默分叉。

⚠️ 断言只碰**形状**（文件名 / 菜单名 / 权限码 / ID 区间 / 有没有碰 Project），
不比对整份 SQL 文本：正文措辞会改，钉死它只会让下一个人改注释也要来改测试。
"""

import re

from pathlib import Path

import pytest

SQL_DIR = Path(__file__).resolve().parents[1] / 'sql'
WIR_SQL_DIR = Path(__file__).resolve().parents[2] / 'wir' / 'sql'

#: `.env.example` 里三种方言都要有 init / init_snowflake / destroy / destroy_snowflake
#: （sqlserver 只走雪花主键，但自增那两份也提供了，plugin.toml 声明了三种库）
DIALECTS = ('mysql', 'postgresql', 'sqlserver')
SCRIPT_KINDS = ('init.sql', 'init_snowflake.sql', 'destroy.sql', 'destroy_snowflake.sql')

MENU_NAMES = (
    'PluginPmMaterial',
    'QueryPmMaterial',
    'AddPmMaterial',
    'EditPmMaterial',
    'DeletePmMaterial',
)
PERMS = ('pm:material:list', 'pm:material:add', 'pm:material:edit', 'pm:material:del')

#: 材料的菜单 ID 区间（WIR 用到 `…000110`，PM 从 `…000201` 起，别撞）
PM_MENU_ID_FLOOR = 2049629108299000201
#: 顶层「项目管理」目录 —— WIR 建的，PM 只引用、不创建、不删除
PROJECT_MENU_ID = '2049629108299000110'


def _read(dialect: str, kind: str) -> str:
    path = SQL_DIR / dialect / kind
    assert path.is_file(), f'缺脚本：{path.relative_to(SQL_DIR.parent.parent)}'
    body = path.read_text(encoding='utf-8')
    assert body.strip(), f'脚本是空的：{path}'
    return body


@pytest.mark.parametrize('dialect', DIALECTS)
def test_every_dialect_has_all_four_scripts(dialect: str) -> None:
    """缺一份的表现是「那个库上静默不建菜单」，不是报错 —— 所以按名字逐个点名"""
    missing = [kind for kind in SCRIPT_KINDS if not (SQL_DIR / dialect / kind).is_file()]
    assert not missing, f'{dialect} 缺这些脚本：{missing}（`get_plugin_sql` 找不到就返回 None，安装照样成功）'

    assert len(list((SQL_DIR / dialect).iterdir())) == len(SCRIPT_KINDS), (
        f'{dialect} 目录里多出别的文件，检查是不是把方言写错层了：'
        f'{sorted(p.name for p in (SQL_DIR / dialect).iterdir())}'
    )


@pytest.mark.parametrize('dialect', DIALECTS)
@pytest.mark.parametrize('kind', ('destroy.sql', 'destroy_snowflake.sql'))
def test_destroy_never_touches_the_shared_project_menu(dialect: str, kind: str) -> None:
    """卸载只删自己那 5 条 + `pm_material`

    `Project` 在这里**一个字符都不该出现** —— 连「先查一下再删」都不需要。
    出现即说明有人想动共用的顶层目录（WIR 台账也跟着没了）。
    """
    body = _read(dialect, kind)

    assert 'Project' not in body, (
        f'{dialect}/{kind} 提到了顶层「项目管理」目录。它是 WIR 建的、两个插件共用 —— '
        '卸 PM 会把 WIR 台账的入口一起删掉，而 WIR 的 destroy 不负责重建它'
    )
    assert '项目管理' not in body, f'{dialect}/{kind} 出现了顶层目录的中文名，卸载脚本不该涉及它'

    missing = [name for name in MENU_NAMES if name not in body]
    assert not missing, f'{dialect}/{kind} 少删了这些菜单行：{missing}'


@pytest.mark.parametrize('dialect', DIALECTS)
@pytest.mark.parametrize('kind', ('destroy.sql', 'destroy_snowflake.sql'))
def test_destroy_drops_the_material_table(dialect: str, kind: str) -> None:
    """非 alembic 部署靠这份脚本清表；不 drop 的话重装会把旧数据留在新菜单下"""
    body = _read(dialect, kind)
    assert re.search(r'drop\s+table\s+if\s+exists\s+pm_material', body, re.IGNORECASE), (
        f'{dialect}/{kind} 没有 `DROP TABLE IF EXISTS pm_material`'
    )


@pytest.mark.parametrize('kind', ('init.sql', 'init_snowflake.sql'))
@pytest.mark.parametrize('dialect', DIALECTS)
def test_init_seeds_the_same_five_menus_and_four_perms(dialect: str, kind: str) -> None:
    """三个方言语义必须一致 —— 缺一条就是那条菜单在某个库上不存在

    权限码也要齐：少一个的表现是「非超管点那个按钮永远 403」，
    而 `test_permission_codes.py` 只要求「后端挂的码在**某个**种子文件里出现过」，
    不要求每个方言都有。
    """
    body = _read(dialect, kind)

    for name in MENU_NAMES:
        assert f"'{name}'" in body, f'{dialect}/{kind} 缺菜单行 {name}'
    for perm in PERMS:
        assert f"'{perm}'" in body, f'{dialect}/{kind} 缺权限码 {perm}'


@pytest.mark.parametrize('dialect', DIALECTS)
def test_init_resolves_the_project_parent_instead_of_creating_it(dialect: str) -> None:
    """自增主键模式的那三份按 `name = 'Project'` 解析父级，**不 INSERT 它**

    PM 是后装的那个插件：`fba add materials` 时顶层目录可能已经由 WIR 建好了。
    再插一条 `Project` 的结果是侧边栏里出现两个「项目管理」。
    """
    body = _read(dialect, 'init.sql')

    assert '项目管理' not in body, 'init 里出现了顶层目录的中文名 —— 那是 WIR 建的，PM 不该重建'

    for match in re.finditer(r"'Project'", body):
        prefix = body[: match.start()]
        assert re.search(r'name\s*=\s*$', prefix, re.IGNORECASE), (
            "init 里 `Project` 只能出现在 `name = 'Project'` 的查询条件里，"
            f'实际上下文：…{body[max(0, match.start() - 60) : match.end() + 20]!r}'
        )


@pytest.mark.parametrize('dialect', DIALECTS)
def test_snowflake_init_uses_fixed_ids_in_the_pm_range(dialect: str) -> None:
    """雪花模式的三份用同一套固定 ID（跨环境可复现），且挂对父子

    - ID 必须 ≥ `…000201`：WIR 已经用掉了 `…000101`–`…000110`
    - 材料页挂 `Project`（`…000110`），四个按钮挂材料页（`…000201`）
    """
    body = _read(dialect, 'init_snowflake.sql')
    ids = {int(value) for value in re.findall(r'\b(204962910829900020\d)\b', body)}

    assert ids == {PM_MENU_ID_FLOOR + offset for offset in range(5)}, f'{dialect} 的固定 ID 集合不对：{sorted(ids)}'

    page_line = next(line for line in body.splitlines() if "'PluginPmMaterial'" in line)
    assert PROJECT_MENU_ID in page_line, f'{dialect} 的材料页没挂在顶层目录 …000110 下：{page_line.strip()}'

    for name in MENU_NAMES[1:]:
        button_line = next(line for line in body.splitlines() if f"'{name}'" in line)
        assert str(PM_MENU_ID_FLOOR) in button_line, (
            f'{dialect} 的按钮 {name} 没挂在材料页 …000201 下：{button_line.strip()}'
        )


@pytest.mark.parametrize('dialect', DIALECTS)
def test_snowflake_ids_do_not_collide_with_wir(dialect: str) -> None:
    """两个插件共用 `sys_menu`，固定 ID 撞了就是**主键冲突**（装第二个插件直接失败）

    WIR 用 `…000101`–`…000110`，PM 从 `…000201` 起。这条按 WIR 的真实文件取数，
    不写死一份「WIR 用了哪些」的清单 —— 那边加菜单时这里自动跟着查。
    """
    wir_paths = sorted(WIR_SQL_DIR.glob('*/init_snowflake.sql'))
    wir_bodies = '\n'.join(path.read_text(encoding='utf-8') for path in wir_paths)
    wir_ids = set(re.findall(r'\b(2049629108299\d{6})\b', wir_bodies))
    assert wir_ids, '没从 WIR 的种子脚本里解析出任何 ID —— 解析坏了，这条会假绿'

    # 方向一：WIR 后来长到 PM 的区间里（PM 先登记了 …000201 起）
    grabbed_by_wir = sorted(pid for pid in wir_ids if int(pid) >= PM_MENU_ID_FLOOR)
    assert not grabbed_by_wir, f'WIR 的 ID 长进了 PM 的区间：{grabbed_by_wir}（装第二个插件会主键冲突）'

    # 方向二：PM 这份文件里**实际写着的** ID 撞上 WIR —— 只查区间会漏掉「抄了个 WIR 的号」。
    # `Project`（…000110）是刻意共用的父级引用，两边都出现是对的，排除掉。
    pm_ids = set(re.findall(r'\b(2049629108299\d{6})\b', _read(dialect, 'init_snowflake.sql')))
    taken_by_pm = sorted((pm_ids & wir_ids) - {PROJECT_MENU_ID})
    assert not taken_by_pm, f'{dialect} 的 init_snowflake.sql 用了 WIR 已经占掉的菜单 ID：{taken_by_pm}'


@pytest.mark.parametrize('dialect', DIALECTS)
def test_non_snowflake_init_does_not_depend_on_generated_ids(dialect: str) -> None:
    """自增主键模式的那三份不写死任何雪花 ID

    它们要能装在「ID 由数据库自增」的库上 —— 写死 `…000201` 会让那一列对不上
    （父级得靠 `name = 'Project'` 解析，见上一条）。
    """
    body = _read(dialect, 'init.sql')
    hardcoded = re.findall(r'\b(2049629108299\d{6})\b', body)
    assert not hardcoded, f'{dialect}/init.sql 里写死了雪花 ID：{hardcoded}（自增主键模式下这些 ID 没有意义）'


def test_sqlserver_init_avoids_declare_and_identity() -> None:
    """sqlserver 自增模式那份不能 `DECLARE` / `SCOPE_IDENTITY()`

    `backend/utils/sql_parser.py` 的白名单只认 `DO` / `INSERT` / `SELECT` / `SET`，
    用了别的动词脚本会在**建库那一刻**被判非法（本地 pytest 不走建库路径，测不出来）。
    父级只能靠 `INSERT … SELECT … FROM sys_menu WHERE name = 'Project'` 解析。
    """
    body = _read('sqlserver', 'init.sql')
    upper = body.upper()

    for forbidden in ('DECLARE', 'SCOPE_IDENTITY'):
        assert forbidden not in upper, f'sqlserver/init.sql 用了 {forbidden}，`parse_sql_script` 的白名单不认'
    assert re.search(r"from\s+sys_menu\s+where\s+name\s*=\s*'Project'", body, re.IGNORECASE), (
        "sqlserver/init.sql 没用 `FROM sys_menu WHERE name = 'Project'` 解析父级"
    )
