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
import { StatusBadge, StatusPill } from "../_shared/status"
import { CUSTOMER_LEVEL_LABEL, type Customer } from "./api"
import type { features } from "./table-features"

const col = createColumnHelper<typeof features, Customer>()

type T = (k: string, vars?: Record<string, unknown>) => string

export function buildColumns(
  onEdit: (c: Customer) => void,
  onDelete: (c: Customer) => void,
  t: T
) {
  return [
    buildSelectColumn(col, {}, t),
    col.accessor("name", {
      header: t("客户名称"),
      cell: ({ getValue }) => <span className="font-medium">{getValue()}</span>,
    }),
    col.accessor("phone", {
      header: t("联系电话"),
      cell: ({ getValue }) => (
        <span className="tabular-nums">{getValue() ?? "—"}</span>
      ),
    }),
    col.accessor("level", {
      header: t("等级"),
      cell: ({ getValue }) => (
        <StatusPill
          tone={
            getValue() === 2 ? "warning" : getValue() === 1 ? "info" : "muted"
          }
        >
          {t(CUSTOMER_LEVEL_LABEL[getValue()] ?? "—")}
        </StatusPill>
      ),
    }),
    col.accessor("status", {
      header: t("状态"),
      cell: ({ getValue }) => <StatusBadge value={getValue()} />,
    }),
    col.accessor("created_time", {
      header: t("创建时间"),
      // 时间一律过 formatDateTime（接口下发的是带偏移的 ISO 串）
      cell: ({ getValue }) => (
        <span className="text-sm text-muted-foreground tabular-nums">
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
                aria-label={t("操作 {{name}}", { name: row.original.name })}
              />
            }
          >
            <IconDotsVertical className="size-4" />
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end" className="w-32">
            <Can perm="crm:customer:edit" fallback={null}>
              <DropdownMenuItem onClick={() => onEdit(row.original)}>
                <IconPencil className="size-4" />
                {t("编辑")}
              </DropdownMenuItem>
            </Can>
            <Can perm="crm:customer:del">
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
  name: "客户名称",
  phone: "联系电话",
  level: "等级",
  status: "状态",
  created_time: "创建时间",
}
