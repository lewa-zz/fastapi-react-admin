/*页面本体：QueryBar + DataTable + listState */
import * as React from "react"
import { useTranslation } from "react-i18next"
import {
  useTable,
  type ColumnVisibilityState,
  type RowSelectionState,
} from "@tanstack/react-table"
import { useQuery } from "@tanstack/react-query"
import { IconPlus, IconSettings, IconUpload } from "@tabler/icons-react"

import { Button } from "@admin/ui/components/button"
import { QueryError } from "@admin/ui/components/query-error"
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
import { ImportSheet } from "../_shared/data-io/import-sheet"
import {
  useDeleteWirRecords,
  wirKeys,
  wirRecordsQuery,
  wirTypesQuery,
  type WirRecord,
  type WirRecordListParams,
} from "./api"
import { COLUMN_LABELS, buildColumns } from "./columns"
import { WirRecordFormSheet } from "./form"
import { WirTypeManager } from "./type-manager"
import { features } from "./table-features"

const DC_OPTIONS = [
  { value: "DC1-Fitout", label: "DC1-Fitout" },
  { value: "DC2-Fitout", label: "DC2-Fitout" },
  { value: "DC3-Fitout", label: "DC3-Fitout" },
]

const DISCIPLINE_OPTIONS = [
  { value: "BMS", label: "BMS" },
  { value: "SEC", label: "SEC" },
  { value: "ELV", label: "ELV" },
]

const DOC_STATUS_OPTIONS = [
  { value: "Approved", label: "Approved" },
  { value: "Approved as Noted", label: "Approved as Noted" },
]

/** 可筛字段。`key` 和接口入参同名，不用 `param` 映射；类型选项在组件里按接口补 */
const BASE_FIELDS: FilterField[] = [
  {
    key: "search",
    label: "搜索",
    type: "text",
    group: "基本信息",
    defaultVisible: true,
    placeholder: "描述 / 别称 / TML / PMWeb",
  },
  {
    key: "dc",
    label: "所属 DC",
    type: "select",
    group: "基本信息",
    defaultVisible: true,
    options: DC_OPTIONS,
  },
  {
    key: "discipline",
    label: "专业",
    type: "select",
    group: "基本信息",
    defaultVisible: true,
    options: DISCIPLINE_OPTIONS,
  },
  {
    key: "doc_status",
    label: "批复状态",
    type: "select",
    group: "状态",
    defaultVisible: true,
    options: DOC_STATUS_OPTIONS,
  },
]

export type WirPageSearch = {
  page?: number
  size?: number
  /** 摆开但还没填值的格子（见 `_shared/use-query-search`） */
  f?: string
  search?: string
  dc?: string
  discipline?: string
  doc_status?: string
  /** 雪花 ID，字符串（硬纪律 6） */
  type_id?: string
}

/**
 * WIR 台账。router-独立（硬纪律 1）：search 只从 props 进、改动经 `onSearchChange` 出，
 * 筛选与分页全进 URL（硬纪律 2）。
 */
export function WirPage({
  search = {},
  onSearchChange,
}: {
  search?: WirPageSearch
  onSearchChange?: (next: WirPageSearch) => void
}) {
  const { t } = useTranslation()
  const page = search.page ?? 1
  const size = search.size ?? DEFAULT_PAGE_SIZE

  const [rowSelection, setRowSelection] = React.useState<RowSelectionState>({})
  const [columnVisibility, setColumnVisibility] =
    React.useState<ColumnVisibilityState>({})

  const typesQuery = useQuery(wirTypesQuery)

  const FIELDS = React.useMemo<FilterField[]>(() => {
    const typeOptions = (typesQuery.data ?? []).map((item) => ({
      value: item.id,
      label: `${item.type_cn} / ${item.type_en}`,
    }))
    return [
      ...BASE_FIELDS,
      {
        key: "type_id",
        label: "类型",
        type: "select",
        group: "基本信息",
        defaultVisible: true,
        options: typeOptions,
        optionsLoading: typesQuery.isPending,
      },
    ]
  }, [typesQuery.data, typesQuery.isPending])

  // 换页 / 换筛选清掉选中：分页在服务端，留着的选中项已不在可见行里
  const patch = React.useCallback(
    (next: Partial<WirPageSearch>) => {
      setRowSelection({})
      onSearchChange?.({ ...search, ...next })
    },
    [onSearchChange, search]
  )

  const q = useQuerySearch({
    fields: FIELDS,
    search,
    onSearchChange,
    refreshKey: wirKeys.records,
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
    wirRecordsQuery({ page, size, ...q.params } as WirRecordListParams)
  )
  const { data, isFetching } = listQuery
  // loading / busy / error / onRetry 一次摊开 —— 接口挂了显示错误块，不是「暂无数据」（硬纪律 9）
  const list = listState(listQuery, {
    onBeforeRefetch: () => setRowSelection({}),
  })
  const rows = data?.items ?? []
  const total = data?.total ?? 0

  const [sheetOpen, setSheetOpen] = React.useState(false)
  const [editing, setEditing] = React.useState<WirRecord | null>(null)
  const [pendingDelete, setPendingDelete] = React.useState<WirRecord | null>(
    null
  )
  const [bulkOpen, setBulkOpen] = React.useState(false)
  const [importOpen, setImportOpen] = React.useState(false)
  const [typeOpen, setTypeOpen] = React.useState(false)
  const del = useDeleteWirRecords()

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
        title={t("WIR 台账")}
        description={t(
          "多 DC 合并的 WIR 提交 / 批复记录；类型是台账的中英对照参考数据。"
        )}
      />

      <ListBody>
        {typesQuery.isError && (
          <QueryError
            error={typesQuery.error}
            onRetry={() => void typesQuery.refetch()}
            title={t("类型列表加载失败")}
          />
        )}
        <QueryBar
          fields={FIELDS}
          value={q.value}
          onChange={q.setValue}
          onSearch={submitQuery}
          onReset={clearFilters}
          applied={q.applied}
          loading={isFetching}
          viewsStorageKey="qb:wir"
          actions={
            <>
              <Can perm="wir:record:add">
                <Button
                  size="sm"
                  onClick={() => {
                    setEditing(null)
                    setSheetOpen(true)
                  }}
                >
                  <IconPlus className="size-4" />
                  {t("新增记录")}
                </Button>
              </Can>
              <Can perm="wir:import">
                <Button
                  size="sm"
                  variant="outline"
                  onClick={() => setImportOpen(true)}
                >
                  <IconUpload className="size-4" />
                  {t("导入台账")}
                </Button>
              </Can>
              <Can perm="wir:type:add">
                <Button
                  size="sm"
                  variant="outline"
                  onClick={() => setTypeOpen(true)}
                >
                  <IconSettings className="size-4" />
                  {t("类型")}
                </Button>
              </Can>
              <RefreshButton busy={isFetching} onClick={list.onRetry} />
              <DataTableColumnVisibility
                table={table}
                columnLabels={COLUMN_LABELS}
              />
              <Can perm="wir:record:del">
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
            /* 10 列 + 长文本，实测最小宽度约 990px：1280 以下的窗口一进来就要横向滚，
               不钉住的话 `…` 跟着内容滚出视口，行操作等于不存在 */
            stickyActions
            rows={table.getRowModel().rows}
            columnCount={columns.length}
            columnLabels={COLUMN_LABELS}
            emptyMessage={t("还没有 WIR 记录")}
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

      <WirRecordFormSheet
        open={sheetOpen}
        onOpenChange={setSheetOpen}
        editing={editing}
      />

      <WirTypeManager open={typeOpen} onOpenChange={setTypeOpen} />

      <ImportSheet
        open={importOpen}
        onOpenChange={setImportOpen}
        base="/api/v1/sys/wir/import"
        title={t("导入 WIR 台账")}
        description={t(
          "支持原始文件的 WIR 表，也支持下载模板填写。带 ID 列时按 ID 判断新增还是更新。"
        )}
        hint={t(
          "如果台账里有类型而类型表还没导入，先到「类型 → 导入类型」导一遍。"
        )}
        invalidate={wirKeys.records}
        modes={["create", "upsert"]}
        previewKeys={["source_id", "dc", "description", "type_id", "tml_no"]}
        testId="wir-import-sheet"
      />

      <ConfirmDialog
        open={pendingDelete !== null}
        onOpenChange={(o) => !o && setPendingDelete(null)}
        title={t("删除 WIR 记录")}
        description={
          pendingDelete
            ? t("确定删除「{{name}}」吗？", {
                name:
                  pendingDelete.tml_no ??
                  pendingDelete.pmweb_no ??
                  pendingDelete.description ??
                  pendingDelete.id,
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
        title={t("批量删除 WIR 记录")}
        description={t("确定删除选中的 {{n}} 条记录吗？", {
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
