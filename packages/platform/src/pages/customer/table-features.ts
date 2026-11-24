/*TanStack Table v9 要注册的特性 */
import {
  columnVisibilityFeature,
  rowPaginationFeature,
  rowSelectionFeature,
  tableFeatures,
} from "@tanstack/react-table"

/** 筛选 / 分页都在服务端；后端固定按 id 倒序、没有排序入参，所以不注册排序特性 */
export const features = tableFeatures({
  columnVisibilityFeature,
  rowPaginationFeature,
  rowSelectionFeature,
})
