# plugin/pm —— 项目管理（材料主数据）

> 扩展级插件（`plugin.toml` 的 `[app] extend = "admin"`），接口最终落在
> **`/api/v1/sys/pm/*`**（不是 `/api/v1/pm/*`，见下）。本卡只有一张表 `pm_material`；
> 指令 / 报价 / 价格变动表（`pm_price_change`）是后续卡。
>
> 这份文件是 [`apps/api` 分册](../../../AGENTS.md) 的**子分册**，Claude Code 读到本目录下的
> 文件时才把它加载进上下文（惰性加载）。跨模块的硬纪律只在根 `CLAUDE.md` 里有一份；
> **新增结论请追加到离代码最近的那一份**。

## 🔴 接口路径比 `plugin.toml` 的 prefix 多一层 `/sys`

`[api.pm] prefix = "/pm"` 只决定插件路由在 `backend.app.admin.api.v1.sys` 路由器下的
相对前缀；那个 sys 路由器本身还带着 `/sys`。所以接口是
`/api/v1/sys/pm/materials`、`/api/v1/sys/pm/materials/{pk}`，`/api/v1/pm/materials` 一条都没有（同 `plugin/wir`）。

- 路由文件名必须是 `api/v1/sys/pm.py` —— 它和 `plugin.toml` 的 `[api.pm]` 靠名字对上，改文件名等于插件路由静默消失。
- 路由声明顺序：`/materials` 在 `/materials/{pk}` **之前**。反过来 `pk` 会吞掉静态路径，报 `422 pk 不是合法整数`。
- `GET /materials` 挂了 `DependsPagination`，分页语句必须带 `ORDER BY`（SQL Server 的 `OFFSET/FETCH` 强制要求），
  排序写在 `CRUDPmMaterial.get_select()` 里走 `select_order('id', 'asc')`，不要挪到接口层拼。

## 字段是按桌面 Excel 实测定的

源文件 `/Users/rico/Desktop/材料表.xlsx`，sheet `Material`，100 条数据 + 1 行合计（跳过）。库列名和表头不一一对应：

| Excel 表头 | 库列 | 为什么 |
|---|---|---|
| `id` | `source_id` | 导入幂等键（同一份表导两次不该多一行）；现在 CRUD 可空 |
| `type` | `kind` | `type` 是 Python 保留字 |
| `Category` | `category` | |
| `mat_CN` / `mat_EN` | `name_cn` / `name_en` | |
| `amo` | `qty` | 合同数量 |
| `"\tunit"`（**表头带制表符**） | `unit` | Excel 里的脏字符，别照抄进列名 |
| `spec` | `spec` | 最长 286 字符且含换行 → `UniversalText`，`UniversalStr` 会截断 |
| `price` / `contract_price` / `in_price` / `out_price` / `market_price` | 同名 | 金额 |

- 金额一律 `mapped_column(sa.Numeric(14, 4))` + `Mapped[Decimal | None]`。**不要 `Mapped[float]`** ——
  SQLAlchemy 2.1 起它映射成 `Double`，SQL Server 上 `test_model_matches_migrations` 会红（同 `alembic` 分册 `cost_time`）。
- 中文列一律 `UniversalStr` / `UniversalText`，不要 `sa.String`。

## 🔴 `source_id` 的唯一约束在 SQL Server 上必须滤掉 NULL

`source_id` 可空（手工建的材料没有源行 ID），而 SQL Server 认为**多个 NULL 彼此相等** —— 普通
`UNIQUE(source_id, deleted)` 下第二条没有 source_id 的材料直接插不进去。模型里的 `_SOURCE_ID_UNIQUE`
就是 `plugin/wir` 的 `_TML_NO_UNIQUE` 同一套写法：非 mssql 用 `UniqueConstraint`，mssql 用带
`mssql_where=source_id IS NOT NULL` 的筛选唯一索引。迁移 `edaef4a6e19f` 里按
`op.get_bind().dialect.name == 'mssql'` 分支，改的时候两边一起改。

## 🔴 不要给 `PmMaterial` 加 relationship

`paging_data()` 最后会对分页结果 `model_dump()`，碰到未加载的关系属性 → SQLAlchemy 惰性加载 →
asyncpg 已离开 greenlet 上下文 → `MissingGreenlet` → 列表 500（`plugin/wir` 的 `wir_type` 就是这么踩的）。
材料没有需要 join 的关联表，别顺手加。

## 菜单：顶层「项目管理」是 WIR 建的、两个插件共用

- 顶层目录 `Project`（`2049629108299000110`，`/project`）由 **WIR** 的种子 / 迁移创建。PM 的 `init*.sql`
  **不 INSERT 它**；`destroy*.sql` 也**只删自己那 5 条**，`DELETE ... name = 'Project'` 会把 WIR 的入口一起删掉。
- PM 的雪花 ID 从 `2049629108299000201` 起（WIR 用到 `…000110`，别撞）。
- 菜单有两处真相源，改一处必须同时改另一处：`sql/*/init_snowflake.sql`（`fba init` / `fba add pm` 走这条）
  和 alembic `edaef4a6e19f` 的 `add_menu`（已存在的库走这条）。改完跑 `pnpm --filter api seed:manifest --write`。
- 迁移里先 `add_menu(Project, parent_name=None)` 再挂 5 条：`insert_if_absent` 按 `name` 幂等，WIR 已装时是 no-op。
- `sqlserver/init.sql`（自增主键模式）**不能用 `DECLARE` / `SCOPE_IDENTITY()`**：`test_sql_scripts.py` 的白名单只认
  `DO` / `INSERT` / `SELECT` / `SET`，父级按 `INSERT … SELECT … FROM sys_menu WHERE name = 'Project' AND deleted = 0` 解析。

## 权限码与数据权限

- 4 个码：`pm:material:list` / `add` / `edit` / `del`，每个写接口都挂了 `Depends(RequestPermission(...))` +
  `DependsRBAC`。漏挂不报错，只表现为**非超管永远 403**；种子菜单里必须有一条带着同一个码（`test_permission_codes.py`）。
- `CRUDPmMaterial.data_scope_enabled = False`：材料是项目级共享主数据，表里没有部门 / 归属人维度，套上行级过滤
  只有 fail-closed 一种效果（受限用户看到 0 条）。理由登记在 `test_data_scope_coverage.py: EXEMPT`，两个方向要对得上。

## 已验证的状态（2026-11-24）

- `db:current` = `edaef4a6e19f (head)`，`down_revision` = `4f7c2a91d3e8`
- 库里有 `pm_material`（`uk_pm_material_source_id_deleted` + 4 个二级索引）和 5 条菜单，`Project` 没被 PM 重建
- 回归：pm 材料 + WIR 导入 + 权限码 / 数据权限覆盖 + `test_sql_scripts` + `test_single_head` → **130 passed**

**本卡没做**：Excel 导入、前端页面、`pm_price_change`、编号器、指令 / 报价。
