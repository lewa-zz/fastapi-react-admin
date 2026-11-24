# plugin/materials —— 材料主数据

- 路由文件：`api/v1/sys/materials.py`。
- 声明顺序：`/materials` 在 `/materials/{pk}` **之前**。

## 字段是按桌面 Excel 实测定的

源文件 `/Users/rico/Desktop/材料表.xlsx`，sheet `Material`，100 条 + 1 行合计。

| Excel 表头                                                             | 库列                  | 为什么                          |
| ---------------------------------------------------------------------- | --------------------- | ------------------------------- |
| `id`                                                                   | `source_id`           | 导入幂等键                      |
| `type`                                                                 | `kind`                | Python 保留字                   |
| `mat_CN` / `mat_EN`                                                    | `name_cn` / `name_en` |                                 |
| `amo`                                                                  | `qty`                 | 合同数量                        |
| `"\tunit"`                                                             | `unit`                | 表头带制表符                    |
| `spec`                                                                 | `spec`                | 最长 286 含换行 → UniversalText |
| `price` / `contract_price` / `in_price` / `out_price` / `market_price` | 同名                  | 金额 Numeric(14,4)              |

- 金额一律 `mapped_column(sa.Numeric(14,4))` + `Mapped[Decimal|None]`。**不要 `Mapped[float]`**。
- 中文列 `UniversalStr` / `UniversalText`。

## 🔴 source_id 唯一约束在 mssql 必须滤 NULL

非 mssql 用 UniqueConstraint，mssql 用 `mssql_where=source_id IS NOT NULL`。

## 🔴 不要加 relationship

`paging_data()` → MissingGreenlet → 列表 500。

## 菜单：Project 由 WIR 创建，共用

- Project（2049629108299000110）不 INSERT 也不 DELETE。
- 雪花 ID 从 2049629108299000201 起。

## 权限码

- `pm:material:list` / `add` / `edit` / `del`
- `data_scope_enabled = False`

## 已验证（2026-11-24）

- alembic `edaef4a6e19f (head)`
- 库有 `pm_material` + 5 条菜单
- 回归全绿
- 路径 `/api/v1/sys/materials`

**未做**：Excel 导入、前端、价格变动、指令/报价。
