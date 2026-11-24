/*页面本体：QueryBar + DataTable + listState */
import * as React from "react"
import { useTranslation } from "react-i18next"
import {
  useTable,
  type ColumnVisibilityState,
  type RowSelectionState,
} from "@tanstack/react-table"
import { useQuery } from "@tanstack/react-query"
import { IconPlus } from "@tabler/icons-react"

import { Button } from "@admin/ui/components/button"
import {
  DataTable,
  DataTableColumnVisibility,
} from "@admin/ui/components/data-table"
import {
  QueryBar,
  countActive,
  type FilterField,
} from "@admin/ui/components/query-bar"

import { Can } from "../../auth/can"
import { ConfirmDialog } from "../../shell/confirm-dialog"
import { PageHeader } from "../../shell/page-header"
import { ListBody, PageShell } from "../_shared/page-shell"
import { BulkBar, RefreshButton, ResetButton } from "../_shared/filters"
import { listState } from "../_shared/list-query"
import { DEFAULT_PAGE_SIZE } from "../_shared/pagination"
import { useQuerySearch } from "../_shared/use-query-search"
import {
  materialsKeys,
  materialsQuery,
  useDeleteMaterials,
  type Material,
  type MaterialListParams,
} from "./api"
import { COLUMN_LABELS, buildColumns } from "./columns"
import { KIND_OPTIONS, MaterialFormSheet } from "./form"
import { DEFAULT_HIDDEN_COLUMNS, features } from "./table-features"

/**
 * 可筛字段。`key` 和接口入参同名，不用 `param` 映射。
 *
 * ⚠️ `category` / `brand` 是**文本模糊匹配**而不是下拉：库里这两个值来自源 Excel
 * 的长文本（`BMS控制柜`、`Schneider`…），后端没有「取不同值」的接口，
 * 固定下拉就只能是空的或者写死一份很快过期的清单 —— 筛不到真数据比没有下拉更糟。
 * 后端补上 distinct 接口之后再换成 `select` + `optionsLoading`。
 */
const FIELDS: FilterField[] = [
  {
    key: "search",
    label: "搜索",
    type: "text",
    group: "基本信息",
    defaultVisible: true,
    // 后端搜的就是这四列
    placeholder: "中文名 / 英文名 / 型号 / 规格",
  },
  {
    key: "kind",
    label: "类型",
    type: "select",
    group: "基本信息",
    defaultVisible: true,
    options: KIND_OPTIONS.map((o) => ({ value: o.value, label: o.label })),
  },
  {
    key: "category",
    label: "类别",
    type: "text",
    group: "基本信息",
    defaultVisible: true,
    placeholder: "模糊匹配",
  },
  {
    key: "brand",
    label: "品牌",
    type: "text",
    group: "基本信息",
    defaultVisible: true,
    placeholder: "模糊匹配",
  },
  {
    key: "active",
    label: "启用",
    type: "boolean",
    group: "状态",
    defaultVisible: true,
  },
]

export type MaterialPageSearch = {
  page?: number
  size?: number
  /** 摆开但还没填值的格子（见 `_shared/use-query-search`） */
  f?: string
  kind?: string
  category?: string
  brand?: string
  /** URL 里是 "true" / "false" 字符串，出参阶段由 QueryBar 按字段类型转回 boolean */
  active?: string
  search?: string
}

/**
 * 材料主数据。router-独立（硬纪律 1）：search 只从 props 进、改动经 `onSearchChange` 出，
 * 筛选与分页全进 URL（硬纪律 2）。
 */
export function MaterialPage({
  search = {},
  onSearchChange,
}: {
  search?: MaterialPageSearch
  onSearchChange?: (next: MaterialPageSearch) => void
}) {
  const { t } = useTranslation()
  const page = search.page ?? 1
  const size = search.size ?? DEFAULT_PAGE_SIZE

  const [rowSelection, setRowSelection] = React.useState<RowSelectionState>({})
  // 21 列一进来全铺开要横滚三轮，先藏掉最不看的三列（见 table-features.ts）
  const [columnVisibility, setColumnVisibility] =
    React.useState<ColumnVisibilityState>(() =>
      Object.fromEntries(DEFAULT_HIDDEN_COLUMNS.map((id) => [id, false]))
    )

  // 换页 / 换筛选清掉选中：分页在服务端，留着的选中项已不在可见行里
  const patch = React.useCallback(
    (next: Partial<MaterialPageSearch>) => {
      setRowSelection({})
      onSearchChange?.({ ...search, ...next })
    },
    [onSearchChange, search]
  )

  const q = useQuerySearch({
    fields: FIELDS,
    search,
    onSearchChange,
    // 传了它，「搜索」才是幂等的：条件没改再点一次也会真的重取（见 hook 注释）
    refreshKey: materialsKeys.all,
  })
  const submitQuery = React.useCallback(
    (v: Parameters<typeof q.submit>[0]) => {
      setRowSelection({})
      q.submit(v)
    },
    [q]
  )
  const clearFilters = React.useCallback(() => {
    setRowSelection({})
    q.reset()
  }, [q])

  const listQuery = useQuery(
    materialsQuery({ page, size, ...q.params } as MaterialListParams)
  )
  const { data, isFetching } = listQuery
  // loading / busy / error / onRetry 一次摊开 —— 接口挂了显示错误块，不是「暂无数据」（硬纪律 9）
  const list = listState(listQuery, {
    onBeforeRefetch: () => setRowSelection({}),
  })
  const rows = data?.items ?? []
  const total = data?.total ?? 0

  const [sheetOpen, setSheetOpen] = React.useState(false)
  const [editing, setEditing] = React.useState<Material | null>(null)
  const [pendingDelete, setPendingDelete] = React.useState<Material | null>(
    null
  )
  const [bulkOpen, setBulkOpen] = React.useState(false)
  const del = useDeleteMaterials()

  const columns = React.useMemo(
    () =>
      buildColumns(
        (r) => {
          setEditing(r)
          setSheetOpen(true)
        },
        setPendingDelete,
        t
      ),
    [t]
  )

  const table = useTable({
    features,
    data: rows,
    columns: columns as never,
    state: { columnVisibility, rowSelection },
    getRowId: (row) => row.id,
    manualPagination: true,
    rowCount: total,
    onColumnVisibilityChange: setColumnVisibility,
    onRowSelectionChange: setRowSelection,
  })

  const selectedIds = Object.keys(rowSelection).filter((k) => rowSelection[k])
  const hasFilter = countActive(q.applied, FIELDS) > 0

  return (
    <PageShell fill="always">
      <PageHeader
        title={t("材料")}
        description={t(
          "BKK03 材料主数据：类型 / 类别 / 规格与合同、报入报出、市场价放在同一行。"
        )}
      />

      <ListBody>
        <QueryBar
          fields={FIELDS}
          value={q.value}
          onChange={q.setValue}
          onSearch={submitQuery}
          onReset={clearFilters}
          applied={q.applied}
          loading={isFetching}
          viewsStorageKey="qb:materials"
          actions={
            <>
              <Can perm="pm:material:add">
                <Button
                  size="sm"
                  onClick={() => {
                    setEditing(null)
                    setSheetOpen(true)
                  }}
                >
                  <IconPlus className="size-4" />
                  {t("新增材料")}
                </Button>
              </Can>
              <RefreshButton busy={isFetching} onClick={list.onRetry} />
              <DataTableColumnVisibility
                table={table}
                columnLabels={COLUMN_LABELS}
              />
              <Can perm="pm:material:del">
                <BulkBar
                  count={selectedIds.length}
                  pending={del.isPending}
                  onDelete={() => setBulkOpen(true)}
                />
              </Can>
            </>
          }
        />

        <div className="content-scroll:flex content-scroll:min-h-0 content-scroll:flex-1 content-scroll:flex-col">
          <DataTable
            table={table}
            showColumnVisibility={false}
            /* 21 列 + 长文本，最小宽度远超桌面视口：不钉住的话 `…` 跟着内容滚出视口，
               行操作等于不存在 */
            stickyActions
            rows={table.getRowModel().rows}
            columnCount={columns.length}
            columnLabels={COLUMN_LABELS}
            emptyMessage={t("还没有材料")}
            emptyAction={
              hasFilter ? (
                <ResetButton
                  variant="outline"
                  label={t("清除筛选")}
                  onClick={clearFilters}
                />
              ) : undefined
            }
            {...list}
            pagination={{
              pageIndex: page - 1,
              pageCount: data?.total_pages ?? 1,
              pageSize: size,
              selectedCount: selectedIds.length,
              totalCount: total,
              onPageChange: (i) => patch({ page: i === 0 ? undefined : i + 1 }),
              onPageSizeChange: (s) => patch({ size: s, page: undefined }),
            }}
          />
        </div>
      </ListBody>

      <MaterialFormSheet
        open={sheetOpen}
        onOpenChange={setSheetOpen}
        editing={editing}
      />

      <ConfirmDialog
        open={pendingDelete !== null}
        onOpenChange={(o) => !o && setPendingDelete(null)}
        title={t("删除材料")}
        description={
          pendingDelete
            ? t("确定删除「{{name}}」吗？", {
                name: pendingDelete.name_cn || pendingDelete.id,
              })
            : ""
        }
        confirmText={t("删除")}
        destructive
        pending={del.isPending}
        onConfirm={async () => {
          if (!pendingDelete) return
          try {
            await del.mutateAsync([pendingDelete.id])
          } finally {
            setPendingDelete(null)
          }
        }}
      />
      <ConfirmDialog
        open={bulkOpen}
        onOpenChange={(o) => !o && setBulkOpen(false)}
        title={t("批量删除材料")}
        description={t("确定删除选中的 {{n}} 条材料吗？", {
          n: selectedIds.length,
        })}
        confirmText={t("删除")}
        destructive
        pending={del.isPending}
        onConfirm={async () => {
          try {
            await del.mutateAsync(selectedIds)
            setRowSelection({})
          } finally {
            setBulkOpen(false)
          }
        }}
      />
    </PageShell>
  )
}
