/*TanStack Table v9 要注册的特性 */
import {
  columnVisibilityFeature,
  rowPaginationFeature,
  rowSelectionFeature,
  tableFeatures,
} from "@tanstack/react-table"

/**
 * 筛选 / 分页都在服务端；后端固定按 id 升序、没有排序入参，所以不注册排序特性
 * （注册了界面上也没有任何东西会变 —— 表头的排序箭头点了不动，比没有更糟）。
 *
 * 操作列钉右不在这里：那是 `DataTable` 的 `stickyActions` prop，列定义里
 * 操作列的 `id` 必须是 `ACTIONS_COLUMN_ID`（= `"actions"`）它才认得出来。
 */
export const features = tableFeatures({
  columnVisibilityFeature,
  rowPaginationFeature,
  rowSelectionFeature,
})

/**
 * 一进页面就藏起来的列。
 *
 * 21 列铺满要横着滚三轮，而 `id`（雪花串）/ `created_time` / `updated_time`
 * 是最不常看的三列 —— 默认藏起来，要看在「列」下拉里勾回来。
 * 状态只活在组件里（不写 URL）：本页 search schema 只有筛选与分页，
 * 而这三列的默认隐藏值必须**始终**成立，写进 URL 反而要额外维护「默认值 vs 显式显示」。
 */
export const DEFAULT_HIDDEN_COLUMNS = ["id", "created_time", "updated_time"]
