# plugin/wir —— WIR 台账（类型参考 · 台账记录 · 菜单权限）

> 扩展级插件（`plugin.toml` 的 `[app] extend = "admin"`），接口最终落在
> **`/api/v1/sys/wir/*`**（不是 `/api/v1/wir/*`，见下）。前端页面是
> `apps/web/src/routes/_auth/project/wir.tsx`（只声明 search / 守卫）+
> `packages/platform/src/pages/wir/`（`/project/wir`，由 `page-registry.tsx` 挂载）。
>
> 这份文件是 [`apps/api` 分册](../../../AGENTS.md) 的**子分册**，Claude Code 读到本目录下的
> 文件时才把它加载进上下文（惰性加载）。跨模块的硬纪律只在根 `CLAUDE.md` 里有一份；
> **新增结论请追加到离代码最近的那一份**。

## 🔴 接口路径比 `plugin.toml` 的 prefix 多一层 `/sys`

`[api.wir] prefix = "/wir"` 只决定插件路由在 **`backend.app.admin.api.v1.sys`**
路由器下的相对前缀；那个 sys 路由器本身还带着 `/sys`。所以扩展级插件写
`extend = "admin"` 时，最终路径是 `/api/v1/sys/wir`、`/api/v1/sys/wir/types`。

**实测**（`app.openapi()['paths']`，2026-11-23）：只有
`/api/v1/sys/wir`、`/api/v1/sys/wir/types`、`/api/v1/sys/wir/types/{pk}`、
`/api/v1/sys/wir/{pk}`；`/api/v1/wir` 一条都没有。前端写请求时别照
`plugin.toml` 里的 prefix 拼。

## 字段长度是按真实 Excel 定的，不是猜的

`WIR Ledger_toDB.xlsx` 实测（289 条记录 / 36 个类型）：

| 字段 | 实测最长 | 列定义 | 为什么 |
|---|---|---|---|
| `pmweb_no` | 166 | `UniversalStr(256)` | 128 会截断 4 行（PostgreSQL 报 `StringDataRightTruncation`） |
| `tml_no` | 21 | `UniversalStr(128)` | 但 **289 行里 243 行是空的** → 唯一约束必须允许 NULL |
| `comment` / `description` | 242 / 61 | `UniversalText` | 顾问意见没有固定上限 |
| `filepath` | 135 | `UniversalStr(1024)` | 存的是「签名件文件名 → 目录」 |
| `type_cn` / `type_en` | 26 / 78 | `UniversalStr(128)` / `(256)` | 中英对照表 |

🔴 `tml_no` 的唯一约束是 `(tml_no, deleted)`，而 SQL Server 认为多个 NULL
彼此相等 —— 那里必须走**筛选唯一索引**（`mssql_where=tml_no IS NOT NULL`），
否则第二条没有 TML 号的记录直接插不进去。模型里的 `_TML_NO_UNIQUE` 就是
`app/admin/model/user.py: _EMAIL_UNIQUE` 的同一套写法。迁移里也按方言分了支
（`op.get_bind().dialect.name == 'mssql'`）。

## 菜单 / 权限码

- **顶层归属是「项目管理」（`Project`，`/project`），不是「系统管理」。** 台账是业务数据，
  和部门 / 角色 / 日志不同类；侧边栏里它和「客户关系」同级（`sort=2`，排在系统管理 1
  之后、日志管理 3 之前）。这条目录由**本插件的种子**创建（`2049629108299000110`），
  卸载时一起删 —— 它目前只有 WIR 一个子项，留在系统种子里会变成删不掉的空目录。
- 种子菜单 ID 用 `2049629108299000101` 起的一段。⚠️ 旧稿里写的 `3000000000000000030`
  是个**不存在的父级**（实测 `select count(*)` = 0）—— 插进去的菜单会变成孤儿，
  被 `traversal_to_tree` 提到侧边栏根上，看着像「顶层凭空多了一条菜单」。
  （最初还挂在 `System` = `2049629108245233667` 下，那是上面那次搬迁之前的形状。）
- 后端挂了守卫的码必须有一条种子菜单带着它，否则非超管**永远 403**
  （守卫：`app/admin/tests/security/test_permission_codes.py`）。WIR 的码：
  `wir:record:list` / `add` / `edit` / `del`、`wir:type:add` / `edit` / `del`
  和导入用的 `wir:import`。
- 菜单数据同时写在两处：`fba init` / `fba add wir` 走 `sql/*/init_snowflake.sql`，
  已存在的库走 alembic 数据迁移（表 / 菜单在 `20261123_1023-590ee6c7b2ea`，
  导入按钮和 `source_id` 在 `20261124_0942-863c8aab994c`，搬迁到「项目管理」在
  `20261124_1100-4f7c2a91d3e8`）。改菜单时两边一起改，
  然后 `pnpm --filter api seed:manifest --write`。
- 🔴 搬迁那条迁移**只在 `PluginWir` 存在时才动手**（插件没装就没有菜单要搬），
  且 `UPDATE` 的 `where` 必须带 `deleted = 0` —— `deleted` 是「0 或这一行自己的 id」
  而不是布尔，漏了会改到一条已软删的菜单，表现是侧边栏凭空多 / 少一条，不报错。
- `sqlserver/init.sql`（自增主键模式）**不能用 `DECLARE` / `SCOPE_IDENTITY()`**：
  `backend/tests/test_sql_scripts.py` 的白名单只认 `DO` / `INSERT` / `SELECT` / `SET`。
  父级按 `INSERT … SELECT … FROM sys_menu WHERE name = '…'` 解析，
  这样也顺带避免了硬编码 ID。

## 前端列表：检查内容在第一列 · 操作列钉在右缘

两处都是实测出来的，不是美观问题：

- **「检查内容」必须在第一列且不截断。** 原来它在第 8 列、`line-clamp-2 max-w-72` ——
  两行之后就没有了，而这一列才是「这条记录在检查什么」，剩下的全是编号。
  现在第一列 `whitespace-normal break-words` + `max-w-[34rem]`（单元格默认是
  `whitespace-nowrap`，不显式覆盖的话长文本不换行）。
- 🔴 **操作列要 `stickyActions`（`DataTable` 的 prop）。** 1600px 视口实测：
  表格 1563px / 容器 1310px，`…` 落在 **x=1792** —— 视口外，用户滚动之前根本看不到，
  反馈就是「这一页没有编辑 / 删除」。钉住之后行操作永远在最后一列。
  表头列和表体列各自吃背景（表体用 `group/row` 跟行的悬停 / 选中底色），
  背景不透明是前提，否则滚过去的单元格会从底下透出来。
- 其余长文本列（类型、TML、PMWeb）改成可换行 + `max-w-[16rem]`：
  不换行的 `whitespace-nowrap` 让这几列各占 200~350px，光它们就把表撑出屏幕。

## 数据权限：两张表都显式豁免

`CRUDWirType` / `CRUDWirRecord` 都写着 `data_scope_enabled = False`：
WIR 台账是**项目级共享记录**，表里没有部门 / 归属人维度，套上过滤只有
fail-closed 一种效果（受限用户看到 0 条），同 `CRUDNotice` / `CRUDDictData`。
豁免理由登记在 `app/admin/tests/security/test_data_scope_coverage.py: EXEMPT`，
那份清单和代码必须两个方向都对得上。

## Excel 导入：两张表、两个资源、先类型后记录

`WIR Ledger_toDB.xlsx` 不是一张表：`WIR`（289 行记录）和 `type`（36 个类型），
记录的 `type_id` 指向类型表的 `id`。所以 `dataio.py` 登记了**两个** `ImportSpec`：

| 资源 | 读哪张表 | 接口 |
|---|---|---|
| `wir.type` | `type`（`sheet_names=('type',)`） | `/api/v1/sys/wir/types/import/{template,preview,commit}` |
| `wir.record` | `WIR`（`sheet_names=('WIR',)`） | `/api/v1/sys/wir/import/{template,preview,commit}` |

- 🔴 **`sheet_names` 是「候选名单」，不是「必须叫这个名字」**：按顺序找，一个都不在时
  回落第一张。所以下载模板填完的文件（只有一张「数据」）和直接导业务文件共用同一份定义。
  这个字段是本插件加进 `ImportSpec` 的（`common/dataio/importing.py`）。
- 🔴 **类型导入保留文件里的原始 ID（1..36）**。记录表的 `type_id` 就是这些数字；
  不保留的话 289 条记录的 `type_id` 全部对不上。`WirType` 的 `id` 是 `init=False`，
  `create_model` 传不进去 —— 先构造模型再 `ins.id = source_id`。
- 记录导入的 `type_id` 两种写法都认：库里的类型 ID，或类型的中文 / 英文名。
  都认不出时报「类型不存在，请先导入类型」，**不会静默写成 NULL**。
- 🔴 **幂等键是 `wir_record.source_id`（源 Excel 的 `ID` 列）**。289 行里 243 行
  没有 TML 号、pmweb_no 里还混着 7 条手写备注，没有任何一个干净的业务键；
  没有它，同一个文件 upsert 一次就多 289 行。`source_id` 列和索引在
  `20261124_0942-863c8aab994c`。
- 导入顺序：**先类型、后记录**。页面把「导入类型」放在类型管理抽屉里、把
  「导入台账」放在列表工具栏，导入抽屉的说明里也写了这句。

## 🔴 列表接口踩过的 MissingGreenlet：`paging_data()` 序列化会碰未加载的关系

**症状**：`GET /api/v1/sys/wir` 稳定 500，日志只有一句
`MissingGreenlet: greenlet_spawn has not been called`，接口本身没有任何 SQL 错误。

**根因**：`paging_data()` 最后对分页结果做 `model_dump()`，而当时 `WirRecord` 上挂着
`wir_type` 关系属性。Pydantic 展开对象时碰到它 → SQLAlchemy 尝试 **lazy load** →
但 asyncpg 已经离开 greenlet 上下文，直接抛 `MissingGreenlet`。

**修法**：这个关系在整个插件里**零调用方**（列表按 `type_id` 批量补中英文名，
详情单独查一次类型），所以直接删掉 `wir_type` 关系，而不是 `noload` ——
`noload` 在 SQLAlchemy 2.1 已废弃（实测会打 `SADeprecationWarning`）。
**以后给会被 `paging_data()` 分页的模型加关系属性时，记得它不是「顺手加一个」**。

**实测**：修前 `pytest` 里 `GET /sys/wir` 500；修后 289 条、类型 36 个、按
`dc` + `type_id` 过滤都 200。回归在 `plugin/wir/tests/test_wir_import.py`（3 条）：
类型表选表 + 源 ID 保留 · 记录导入按 ID / 名称映射且 upsert 幂等 · 未知类型报错而不是写 NULL。
