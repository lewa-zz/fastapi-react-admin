/** @file 材料主数据 API
 * 类型 · query key · queryOptions · mutation
 *
 * 接口前缀是 `/api/v1/sys/materials`（插件 `extend = "admin"` 多一层 `/sys`，
 * 见 `apps/api/backend/plugin/materials/AGENTS.md`），不是 `/api/v1/materials`。
 */
import {
  queryOptions,
  useMutation,
  useQueryClient,
} from "@tanstack/react-query"

import { api, type PageData } from "../../api-client/client"

/**
 * 数量 / 金额的出网形态。
 *
 * 后端是 `Numeric(14,4)` + `Decimal`，序列化后**可能是字符串**（`"12.5000"`，
 * pydantic 的默认行为），也可能是数字 —— 只按一种写，另一种就会在单元格里
 * 变成 `NaN` 或者原样铺出四位小数。凡是渲染金额/数量，一律先过 `toNumber()`。
 */
export type Decimalish = number | string | null

/** 雪花 ID 一律字符串，不要 `Number()`（硬纪律 6） */
export type Material = {
  id: string
  /** 来源 Excel 行 ID（导入幂等键），手工新增的是 null */
  source_id: number | null
  /** PLC / Program（编程/软件） / Sensor（现场安装）—— 后端原样存这一串 */
  kind: string
  category: string
  name_cn: string
  name_en: string
  model: string | null
  /** 规格含换行（源 Excel 最长 286 字符），列表里要截断 + tooltip */
  spec: string | null
  brand: string | null
  qty: Decimalish
  unit: string
  price: Decimalish
  contract_price: Decimalish
  in_price: Decimalish
  out_price: Decimalish
  market_price: Decimalish
  memo: string | null
  source: string | null
  currency: string
  active: boolean
  created_time: string
  updated_time: string | null
}

/** 创建 / 更新的请求体。`kind` / `category` / `name_*` / `unit` 后端是必填 */
export type MaterialBody = {
  /** 不传 = 手工新增；传了就必须唯一（撞了后端 409） */
  source_id: number | null
  kind: string
  category: string
  name_cn: string
  name_en: string
  model: string | null
  spec: string | null
  brand: string | null
  qty: number | null
  unit: string
  price: number | null
  contract_price: number | null
  in_price: number | null
  out_price: number | null
  market_price: number | null
  memo: string | null
  source: string | null
  currency: string
  active: boolean
}

export type MaterialListParams = {
  page: number
  size: number
  kind?: string
  category?: string
  brand?: string
  /** 不传 = 全部（后端 `active: bool | None`） */
  active?: boolean
  /** 后端搜的是 name_cn / name_en / model / spec */
  search?: string
}

const BASE = "/api/v1/sys/materials"

export const materialsKeys = {
  all: ["materials"] as const,
  list: (p: MaterialListParams) => [...materialsKeys.all, p] as const,
  detail: (id: string) => [...materialsKeys.all, "detail", id] as const,
}

/** `12.5000` / `12.5` / `null` → `12.5` / `12.5` / `null`；不是数字就当没有 */
export function toNumber(value: Decimalish): number | null {
  if (value === null || value === "") return null
  const n = typeof value === "number" ? value : Number(value)
  return Number.isFinite(n) ? n : null
}

function qs(p: MaterialListParams): string {
  const s = new URLSearchParams()
  s.set("page", String(p.page))
  s.set("size", String(p.size))
  if (p.kind) s.set("kind", p.kind)
  if (p.category) s.set("category", p.category)
  if (p.brand) s.set("brand", p.brand)
  // ⚠️ 用 `!== undefined` 判，不要写成 `if (p.active)` —— 那样「只看停用」永远发不出去
  if (p.active !== undefined) s.set("active", p.active ? "true" : "false")
  if (p.search) s.set("search", p.search)
  return s.toString()
}

export const materialsQuery = (p: MaterialListParams) =>
  queryOptions({
    queryKey: materialsKeys.list(p),
    queryFn: () => api.GET<PageData<Material>>(`${BASE}?${qs(p)}`),
    // 翻页时保留上一页，避免表格闪空
    placeholderData: (prev) => prev,
  })

export const materialQuery = (id: string) =>
  queryOptions({
    queryKey: materialsKeys.detail(id),
    queryFn: () => api.GET<Material>(`${BASE}/${id}`),
    enabled: Boolean(id),
  })

function useInvalidate() {
  const qc = useQueryClient()
  return () => qc.invalidateQueries({ queryKey: materialsKeys.all })
}

export function useCreateMaterial() {
  const invalidate = useInvalidate()
  return useMutation({
    mutationFn: (body: MaterialBody) => api.POST(BASE, { body }),
    onSuccess: invalidate,
    // 表单里内联显示后端的报错，全局 toast 再弹一遍只是噪音
    meta: { suppressErrorToast: true },
  })
}

export function useUpdateMaterial() {
  const invalidate = useInvalidate()
  return useMutation({
    mutationFn: ({ id, body }: { id: string; body: MaterialBody }) =>
      api.PUT(`${BASE}/${id}`, { body }),
    onSuccess: invalidate,
    meta: { suppressErrorToast: true },
  })
}

export function useDeleteMaterials() {
  const invalidate = useInvalidate()
  return useMutation({
    mutationFn: (pks: string[]) => api.DELETE(BASE, { body: { pks } }),
    onSuccess: invalidate,
  })
}
