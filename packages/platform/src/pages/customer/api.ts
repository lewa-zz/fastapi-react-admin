/** @file 客户管理 API
 * 类型 · query key · queryOptions · mutation
 */
import {
  queryOptions,
  useMutation,
  useQueryClient,
} from "@tanstack/react-query"

import { api, type PageData } from "../../api-client/client"

/** 雪花 ID 一律字符串，不要 `Number()`（硬纪律 6） */
export type Customer = {
  id: string
  name: string
  phone: string | null
  /** 0 普通 · 1 重要 · 2 VIP */
  level: number
  /** 0 停用 · 1 正常 */
  status: number
  dept_id: string | null
  owner_id: string | null
  created_by: string
  remark: string | null
  created_time: string
  updated_time: string | null
}

export type CustomerBody = {
  name: string
  phone: string | null
  level: number
  status: number
  remark: string | null
}

export type CustomerListParams = {
  page: number
  size: number
  name?: string
  phone?: string
  level?: number
  status?: number
}

/** 等级的中文即语言包 key，渲染处过 `t()` */
export const CUSTOMER_LEVEL_LABEL: Record<number, string> = {
  0: "普通",
  1: "重要",
  2: "VIP",
}

const BASE = "/api/v1/crm/customers"

export const customerKeys = {
  all: ["crm", "customer"] as const,
  list: (p: CustomerListParams) => [...customerKeys.all, "list", p] as const,
}

function qs(p: CustomerListParams): string {
  const s = new URLSearchParams()
  s.set("page", String(p.page))
  s.set("size", String(p.size))
  if (p.name) s.set("name", p.name)
  if (p.phone) s.set("phone", p.phone)
  if (p.level !== undefined) s.set("level", String(p.level))
  if (p.status !== undefined) s.set("status", String(p.status))
  return s.toString()
}

export const customersQuery = (p: CustomerListParams) =>
  queryOptions({
    queryKey: customerKeys.list(p),
    queryFn: () => api.GET<PageData<Customer>>(`${BASE}?${qs(p)}`),
    // 翻页时保留上一页，避免表格闪空
    placeholderData: (prev) => prev,
  })

function useInvalidate() {
  const qc = useQueryClient()
  return () => qc.invalidateQueries({ queryKey: customerKeys.all })
}

export function useCreateCustomer() {
  const invalidate = useInvalidate()
  return useMutation({
    mutationFn: (body: CustomerBody) => api.POST(BASE, { body }),
    onSuccess: invalidate,
    // 表单里内联显示后端的报错，全局 toast 再弹一遍只是噪音
    meta: { suppressErrorToast: true },
  })
}

export function useUpdateCustomer() {
  const invalidate = useInvalidate()
  return useMutation({
    mutationFn: ({ id, body }: { id: string; body: CustomerBody }) =>
      api.PUT(`${BASE}/${id}`, { body }),
    onSuccess: invalidate,
    meta: { suppressErrorToast: true },
  })
}

export function useDeleteCustomers() {
  const invalidate = useInvalidate()
  return useMutation({
    mutationFn: (pks: string[]) => api.DELETE(BASE, { body: { pks } }),
    onSuccess: invalidate,
  })
}
