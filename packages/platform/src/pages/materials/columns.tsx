/* 列定义 + 行操作（按钮用 <Can> 包住）*/
import type { ReactNode } from "react"
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
import { EmptyCell } from "../_shared/cells"
import { buildSelectColumn } from "../_shared/select-column"
import { StatusPill, YesNoBadge, type Tone } from "../_shared/status"
import { toNumber, type Decimalish, type Material } from "./api"
import type { features } from "./table-features"

const col = createColumnHelper<typeof features, Material>()

type T = (k: string, vars?: Record<string, unknown>) => string

/** 金额统一两位小数（Excel 里的 `price` 等列就是这个口径） */
const AMOUNT_FMT = new Intl.NumberFormat("en-US", {
  minimumFractionDigits: 2,
  maximumFractionDigits: 2,
})

/** 数量最多到四位（`Numeric(14,4)`），整数不补零 —— 「12 台」不该显示成「12.0000」 */
const QTY_FMT = new Intl.NumberFormat("en-US", { maximumFractionDigits: 4 })

/** 表头也跟着右对齐，否则数字列的头在左、值在右，看起来像两列错开 */
function NumHeader({ children }: { children: ReactNode }) {
  return <span className="block text-end">{children}</span>
}

function Amount({ value }: { value: Decimalish }) {
  const n = toNumber(value)
  if (n === null) return <EmptyCell />
  return (
    <span className="block text-end tabular-nums">{AMOUNT_FMT.format(n)}</span>
  )
}

function Qty({ value }: { value: Decimalish }) {
  const n = toNumber(value)
  if (n === null) return <EmptyCell />
  return <span className="block text-end tabular-nums">{QTY_FMT.format(n)}</span>
}

/** 长文本：截一行 + `title` 给全量（规格含换行，撑开会把整行顶高） */
const TRUNCATE_CELL = "block max-w-[16rem] truncate"

/** 来源 Excel 的 kind 是三种，色只是为了扫得快，不是业务状态 */
const KIND_TONE: Record<string, Tone> = {
  PLC: "info",
  "Program（编程/软件）": "warning",
  "Sensor（现场安装）": "success",
}

export function buildColumns(
  onEdit: (r: Material) => void,
  onDelete: (r: Material) => void,
  t: T
) {
  return [
    buildSelectColumn(col, {}, t),
    col.accessor("id", {
      header: t("#"),
      cell: ({ getValue }) => (
        <span className="font-mono text-xs text-muted-foreground">
          {getValue()}
        </span>
      ),
    }),
    col.accessor("kind", {
      header: t("类型"),
      cell: ({ getValue }) => {
        const value = getValue()
        if (!value) return <EmptyCell />
        return (
          <StatusPill tone={KIND_TONE[value] ?? "muted"}>{value}</StatusPill>
        )
      },
    }),
    col.accessor("category", {
      header: t("类别"),
      cell: ({ getValue }) => (
        <span className={TRUNCATE_CELL} title={getValue() ?? undefined}>
          {getValue() ?? "—"}
        </span>
      ),
    }),
    col.accessor("name_cn", {
      header: t("中文名"),
      cell: ({ getValue }) => (
        <span className="font-medium">{getValue() || "—"}</span>
      ),
    }),
    col.accessor("name_en", {
      header: t("英文名"),
      cell: ({ getValue }) => (
        <span className={TRUNCATE_CELL} title={getValue() || undefined}>
          {getValue() || "—"}
        </span>
      ),
    }),
    col.accessor("model", {
      header: t("型号"),
      cell: ({ getValue }) => (
        <span className={TRUNCATE_CELL} title={getValue() ?? undefined}>
          {getValue() ?? "—"}
        </span>
      ),
    }),
    col.accessor("spec", {
      header: t("规格"),
      // 含换行、最长 286 字符：整段铺出来会把这一行顶成五六行高。截断 + tooltip
      cell: ({ getValue }) => (
        <span className={TRUNCATE_CELL} title={getValue() ?? undefined}>
          {getValue() ?? "—"}
        </span>
      ),
    }),
    col.accessor("brand", {
      header: t("品牌"),
      cell: ({ getValue }) => (
        <span className={TRUNCATE_CELL} title={getValue() ?? undefined}>
          {getValue() ?? "—"}
        </span>
      ),
    }),
    col.accessor("qty", {
      header: () => <NumHeader>{t("数量")}</NumHeader>,
      cell: ({ getValue }) => <Qty value={getValue()} />,
    }),
    col.accessor("unit", {
      header: t("单位"),
      cell: ({ getValue }) => (
        <span className="whitespace-nowrap">{getValue() || "—"}</span>
      ),
    }),
    col.accessor("price", {
      header: () => <NumHeader>{t("合同单价")}</NumHeader>,
      cell: ({ getValue }) => <Amount value={getValue()} />,
    }),
    col.accessor("contract_price", {
      header: () => <NumHeader>{t("合同合价")}</NumHeader>,
      cell: ({ getValue }) => <Amount value={getValue()} />,
    }),
    col.accessor("in_price", {
      header: () => <NumHeader>{t("报入单价")}</NumHeader>,
      cell: ({ getValue }) => <Amount value={getValue()} />,
    }),
    col.accessor("out_price", {
      header: () => <NumHeader>{t("报出价")}</NumHeader>,
      cell: ({ getValue }) => <Amount value={getValue()} />,
    }),
    col.accessor("market_price", {
      header: () => <NumHeader>{t("市场价")}</NumHeader>,
      cell: ({ getValue }) => <Amount value={getValue()} />,
    }),
    col.accessor("memo", {
      header: t("备注"),
      cell: ({ getValue }) => (
        <span className={TRUNCATE_CELL} title={getValue() ?? undefined}>
          {getValue() ?? "—"}
        </span>
      ),
    }),
    col.accessor("source", {
      header: t("来源"),
      cell: ({ getValue }) => (
        <span className={TRUNCATE_CELL} title={getValue() ?? undefined}>
          {getValue() ?? "—"}
        </span>
      ),
    }),
    col.accessor("currency", {
      header: t("币种"),
      cell: ({ getValue }) => (
        <span className="whitespace-nowrap">{getValue() || "—"}</span>
      ),
    }),
    col.accessor("active", {
      header: t("启用"),
      cell: ({ getValue }) => (
        <YesNoBadge value={getValue()} yes="是" no="否" />
      ),
    }),
    col.accessor("created_time", {
      header: t("创建时间"),
      // 时间一律过 formatDateTime（接口下发的是带偏移的 ISO 串），空值它自己给「—」
      cell: ({ getValue }) => (
        <span className="text-sm text-muted-foreground tabular-nums whitespace-nowrap">
          {formatDateTime(getValue())}
        </span>
      ),
    }),
    col.accessor("updated_time", {
      header: t("更新时间"),
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
                  name: row.original.name_cn || row.original.id,
                })}
              />
            }
          >
            <IconDotsVertical className="size-4" />
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end" className="w-32">
            <Can perm="pm:material:edit" fallback={null}>
              <DropdownMenuItem onClick={() => onEdit(row.original)}>
                <IconPencil className="size-4" />
                {t("编辑")}
              </DropdownMenuItem>
            </Can>
            <Can perm="pm:material:del">
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

/** 「列」下拉里显示的中文名 —— 少了哪一列，那一列在面板上就显示成字段名 */
export const COLUMN_LABELS: Record<string, string> = {
  id: "#",
  kind: "类型",
  category: "类别",
  name_cn: "中文名",
  name_en: "英文名",
  model: "型号",
  spec: "规格",
  brand: "品牌",
  qty: "数量",
  unit: "单位",
  price: "合同单价",
  contract_price: "合同合价",
  in_price: "报入单价",
  out_price: "报出价",
  market_price: "市场价",
  memo: "备注",
  source: "来源",
  currency: "币种",
  active: "启用",
  created_time: "创建时间",
  updated_time: "更新时间",
}
