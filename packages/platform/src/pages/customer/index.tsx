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
  customerKeys,
  customersQuery,
  useDeleteCustomers,
  type Customer,
  type CustomerListParams,
} from "./api"
import { COLUMN_LABELS, buildColumns } from "./columns"
import { CustomerFormSheet } from "./form"
import { features } from "./table-features"

/** 可筛字段。`key` 和接口入参同名，不用 `param` 映射 */
const FIELDS: FilterField[] = [
  {
    key: "name",
    label: "客户名称",
    type: "text",
    group: "基本信息",
    defaultVisible: true,
    placeholder: "模糊匹配",
  },
  {
    key: "phone",
    label: "联系电话",
    type: "text",
    group: "基本信息",
    defaultVisible: true,
    placeholder: "模糊匹配",
  },
  {
    key: "level",
    label: "等级",
    type: "select",
    group: "基本信息",
    defaultVisible: true,
    options: [
      { value: 0, label: "普通" },
      { value: 1, label: "重要" },
      { value: 2, label: "VIP" },
    ],
  },
  {
    key: "status",
    label: "状态",
    type: "select",
    group: "状态",
    defaultVisible: true,
    options: [
      { value: 1, label: "正常" },
      { value: 0, label: "停用" },
    ],
  },
]

export type CustomerPageSearch = {
  page?: number
  size?: number
  /** 摆开但还没填值的格子（见 `_shared/use-query-search`） */
  f?: string
  name?: string
  phone?: string
  level?: number
  status?: number
}

/**
 * 客户管理。router-独立（硬纪律 1）：search 只从 props 进、改动经 `onSearchChange` 出，
 * 筛选与分页全进 URL（硬纪律 2）。
 */
export function CustomerPage({
  search = {},
  onSearchChange,
}: {
  search?: CustomerPageSearch
  onSearchChange?: (next: CustomerPageSearch) => void
}) {
  const { t } = useTranslation()
  const page = search.page ?? 1
  const size = search.size ?? DEFAULT_PAGE_SIZE

  const [rowSelection, setRowSelection] = React.useState<RowSelectionState>({})
  const [columnVisibility, setColumnVisibility] =
    React.useState<ColumnVisibilityState>({})

  // 换页 / 换筛选清掉选中：分页在服务端，留着的选中项已不在可见行里
  const patch = React.useCallback(
    (next: Partial<CustomerPageSearch>) => {
      setRowSelection({})
      onSearchChange?.({ ...search, ...next })
    },
    [onSearchChange, search]
  )

  const q = useQuerySearch({
    fields: FIELDS,
    search,
    onSearchChange,
    refreshKey: customerKeys.all,
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
    customersQuery({ page, size, ...q.params } as CustomerListParams)
  )
  const { data, isFetching } = listQuery
  // loading / busy / error / onRetry 一次摊开 —— 接口挂了显示错误块，不是「暂无数据」（硬纪律 9）
  const list = listState(listQuery, {
    onBeforeRefetch: () => setRowSelection({}),
  })
  const rows = data?.items ?? []
  const total = data?.total ?? 0

  const [sheetOpen, setSheetOpen] = React.useState(false)
  const [editing, setEditing] = React.useState<Customer | null>(null)
  const [pendingDelete, setPendingDelete] = React.useState<Customer | null>(
    null
  )
  const [bulkOpen, setBulkOpen] = React.useState(false)
  const del = useDeleteCustomers()

  const columns = React.useMemo(
    () =>
      buildColumns(
        (c) => {
          setEditing(c)
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
        title={t("客户管理")}
        description={t("维护客户档案；能看到哪些客户由数据权限决定。")}
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
          viewsStorageKey="qb:customer"
          actions={
            <>
              <Can perm="crm:customer:add">
                <Button
                  size="sm"
                  onClick={() => {
                    setEditing(null)
                    setSheetOpen(true)
                  }}
                >
                  <IconPlus className="size-4" />
                  {t("新增客户")}
                </Button>
              </Can>
              <RefreshButton busy={isFetching} onClick={list.onRetry} />
              <DataTableColumnVisibility
                table={table}
                columnLabels={COLUMN_LABELS}
              />
              <Can perm="crm:customer:del">
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
            rows={table.getRowModel().rows}
            columnCount={columns.length}
            columnLabels={COLUMN_LABELS}
            emptyMessage={t("还没有客户")}
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

      <CustomerFormSheet
        open={sheetOpen}
        onOpenChange={setSheetOpen}
        editing={editing}
      />

      <ConfirmDialog
        open={pendingDelete !== null}
        onOpenChange={(o) => !o && setPendingDelete(null)}
        title={t("删除客户")}
        description={
          pendingDelete
            ? t("确定删除「{{name}}」吗？", { name: pendingDelete.name })
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
        title={t("批量删除客户")}
        description={t("确定删除选中的 {{n}} 个客户吗？", {
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
