/* 列定义 + 行操作（按钮用 <Can> 包住）*/
import { createColumnHelper } from "@tanstack/react-table"
import { IconDotsVertical, IconPencil, IconTrash } from "@tabler/icons-react"

import { formatDateTime } from "@admin/i18n"
import { Button } from "@admin/ui/components/button"
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@admin/ui/components/dropdown-menu"

import { Can } from "../../auth/can"
import { buildSelectColumn } from "../_shared/select-column"
import { StatusPill, type Tone } from "../_shared/status"
import type { WirRecord } from "./api"
import type { features } from "./table-features"

const col = createColumnHelper<typeof features, WirRecord>()

type T = (k: string, vars?: Record<string, unknown>) => string

/** 批复状态的色：只有「Approved」是绿的，「as Noted」是带条件通过 */
const STATUS_TONE: Record<string, Tone> = {
  Approved: "success",
  "Approved as Noted": "warning",
  Rejected: "danger",
  Pending: "info",
}

/**
 * 🔴 「检查内容」放在**第一列**，而且不许截断。
 *
 * 实测这份台账里最长的一条 61 个字（`WIR Ledger_toDB.xlsx`），原来那格是
 * `line-clamp-2 max-w-72` —— 两行以后就没了，而这一列正是「这条记录到底在检查什么」，
 * 截掉之后整张表只剩编号，看不出内容。
 *
 * 单元格默认是 `whitespace-nowrap`（`table.tsx` 的 `TableCell`），所以这里必须
 * 显式 `whitespace-normal` + `break-words`：长编号（`PMWeb 编号` 最长 166 字符）
 * 里没有空格，光换行断不开。宽度用 `max-w-*` 给上限，让它在多行里铺开而不是
 * 把整张表撑出屏幕。
 */
const DESCRIPTION_CELL =
  "block max-w-[34rem] min-w-[14rem] text-sm whitespace-normal break-words"

/** 编号 / 类型这类长文本：可以换行，但别无限宽 —— 否则一行占掉半张表 */
const WRAP_CELL = "block max-w-[16rem] whitespace-normal break-words"

export function buildColumns(
  onEdit: (r: WirRecord) => void,
  onDelete: (r: WirRecord) => void,
  t: T
) {
  return [
    buildSelectColumn(col, {}, t),
    col.accessor("description", {
      header: t("检查内容"),
      cell: ({ getValue }) => (
        <span className={DESCRIPTION_CELL}>{getValue() ?? "—"}</span>
      ),
    }),
    col.accessor("type_cn", {
      header: t("类型"),
      cell: ({ row }) => (
        <span className={WRAP_CELL}>
          {row.original.type_cn ?? row.original.type_en ?? "—"}
        </span>
      ),
    }),
    col.accessor("dc", {
      header: t("所属 DC"),
      cell: ({ getValue }) => (
        <span className="whitespace-nowrap">{getValue() ?? "—"}</span>
      ),
    }),
    col.accessor("discipline", {
      header: t("专业"),
      cell: ({ getValue }) => (
        <span className="whitespace-nowrap">{getValue() ?? "—"}</span>
      ),
    }),
    col.accessor("doc_status", {
      header: t("批复状态"),
      cell: ({ getValue }) => {
        const value = getValue()
        if (!value) return <span className="text-muted-foreground">—</span>
        return (
          <StatusPill tone={STATUS_TONE[value] ?? "muted"}>{value}</StatusPill>
        )
      },
    }),
    col.accessor("tml_no", {
      header: t("TML 编号"),
      cell: ({ getValue }) => (
        <span className={`${WRAP_CELL} font-mono text-xs`}>
          {getValue() ?? "—"}
        </span>
      ),
    }),
    col.accessor("pmweb_no", {
      header: t("PMWeb 编号"),
      cell: ({ getValue }) => (
        <span className={`${WRAP_CELL} font-mono text-xs`}>
          {getValue() ?? "—"}
        </span>
      ),
    }),
    col.accessor("drt_submitted", {
      header: t("DRT 提交日期"),
      cell: ({ getValue }) => (
        <span className="text-sm text-muted-foreground tabular-nums whitespace-nowrap">
          {formatDateTime(getValue())}
        </span>
      ),
    }),
    col.display({
      id: "actions",
      header: () => <span className="sr-only">{t("操作")}</span>,
      cell: ({ row }) => (
        <DropdownMenu>
          <DropdownMenuTrigger
            render={
              <Button
                variant="ghost"
                size="icon"
                className="size-7"
                aria-label={t("操作 {{name}}", {
                  name:
                    row.original.tml_no ??
                    row.original.pmweb_no ??
                    row.original.id,
                })}
              />
            }
          >
            <IconDotsVertical className="size-4" />
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end" className="w-32">
            <Can perm="wir:record:edit" fallback={null}>
              <DropdownMenuItem onClick={() => onEdit(row.original)}>
                <IconPencil className="size-4" />
                {t("编辑")}
              </DropdownMenuItem>
            </Can>
            <Can perm="wir:record:del">
              <DropdownMenuItem
                variant="destructive"
                onClick={() => onDelete(row.original)}
              >
                <IconTrash className="size-4" />
                {t("删除")}
              </DropdownMenuItem>
            </Can>
          </DropdownMenuContent>
        </DropdownMenu>
      ),
    }),
  ]
}

export const COLUMN_LABELS: Record<string, string> = {
  description: "检查内容",
  type_cn: "类型",
  dc: "所属 DC",
  discipline: "专业",
  doc_status: "批复状态",
  tml_no: "TML 编号",
  pmweb_no: "PMWeb 编号",
  drt_submitted: "DRT 提交日期",
}
