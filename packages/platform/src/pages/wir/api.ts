/** @file WIR 台账 API
 * 类型 · query key · queryOptions · mutation
 *
 * 接口前缀是 `/api/v1/sys/wir`（插件 `extend = "admin"` 多一层 `/sys`，
 * 见 `apps/api/backend/plugin/wir/AGENTS.md`），不是 `/api/v1/wir`。
 */
import {
  queryOptions,
  useMutation,
  useQueryClient,
} from "@tanstack/react-query"

import { api, type PageData } from "../../api-client/client"

/** 雪花 ID 一律字符串，不要 `Number()`（硬纪律 6） */
export type WirType = {
  id: string
  type_cn: string
  type_en: string
}

export type WirRecord = {
  id: string
  from_party: string | null
  tml_no: string | null
  pmweb_no: string | null
  doc_type: string | null
  discipline: string | null
  description: string | null
  drt_submitted: string | null
  pmx_submitted: string | null
  cb_inspection: string | null
  doc_status: string | null
  comment: string | null
  another_desc: string | null
  dc: string | null
  filepath: string | null
  /** 雪花 ID，字符串 */
  type_id: string | null
  type_cn: string | null
  type_en: string | null
  created_time: string
  updated_time: string | null
}

/** 日期只到天，但接口字段是 datetime —— 统一发当天 00:00（按显示时区，见 `wall-time.ts`） */
export type WirRecordBody = {
  from_party: string | null
  tml_no: string | null
  pmweb_no: string | null
  doc_type: string | null
  discipline: string | null
  description: string | null
  drt_submitted: string | null
  pmx_submitted: string | null
  cb_inspection: string | null
  doc_status: string | null
  comment: string | null
  another_desc: string | null
  dc: string | null
  filepath: string | null
  /** 提交的是字符串，后端 pydantic 按 int 收（照样不能 `Number()`） */
  type_id: string | null
}

export type WirTypeBody = {
  type_cn: string
  type_en: string
}

export type WirRecordListParams = {
  page: number
  size: number
  dc?: string
  discipline?: string
  doc_status?: string
  type_id?: string
  search?: string
}

const BASE = "/api/v1/sys/wir"

export const wirKeys = {
  all: ["wir"] as const,
  records: ["wir", "records"] as const,
  list: (p: WirRecordListParams) => [...wirKeys.records, "list", p] as const,
  types: ["wir", "types"] as const,
}

function qs(p: WirRecordListParams): string {
  const s = new URLSearchParams()
  s.set("page", String(p.page))
  s.set("size", String(p.size))
  if (p.dc) s.set("dc", p.dc)
  if (p.discipline) s.set("discipline", p.discipline)
  if (p.doc_status) s.set("doc_status", p.doc_status)
  if (p.type_id) s.set("type_id", p.type_id)
  if (p.search) s.set("search", p.search)
  return s.toString()
}

export const wirRecordsQuery = (p: WirRecordListParams) =>
  queryOptions({
    queryKey: wirKeys.list(p),
    queryFn: () => api.GET<PageData<WirRecord>>(`${BASE}?${qs(p)}`),
    // 翻页时保留上一页，避免表格闪空
    placeholderData: (prev) => prev,
  })

export const wirTypesQuery = queryOptions({
  queryKey: wirKeys.types,
  queryFn: () => api.GET<WirType[]>(`${BASE}/types`),
  // 类型是下拉参考数据，改一次之后所有页面共用同一份
  staleTime: 60_000,
})

function useInvalidateRecords() {
  const qc = useQueryClient()
  return () => qc.invalidateQueries({ queryKey: wirKeys.records })
}

function useInvalidateTypes() {
  const qc = useQueryClient()
  return () => qc.invalidateQueries({ queryKey: wirKeys.types })
}

export function useCreateWirRecord() {
  const invalidate = useInvalidateRecords()
  return useMutation({
    mutationFn: (body: WirRecordBody) => api.POST(BASE, { body }),
    onSuccess: invalidate,
    // 表单里内联显示后端的报错，全局 toast 再弹一遍只是噪音
    meta: { suppressErrorToast: true },
  })
}

export function useUpdateWirRecord() {
  const invalidate = useInvalidateRecords()
  return useMutation({
    mutationFn: ({ id, body }: { id: string; body: WirRecordBody }) =>
      api.PUT(`${BASE}/${id}`, { body }),
    onSuccess: invalidate,
    meta: { suppressErrorToast: true },
  })
}

export function useDeleteWirRecords() {
  const invalidate = useInvalidateRecords()
  return useMutation({
    mutationFn: (pks: string[]) => api.DELETE(BASE, { body: { pks } }),
    onSuccess: invalidate,
  })
}

export function useCreateWirType() {
  const invalidate = useInvalidateTypes()
  return useMutation({
    mutationFn: (body: WirTypeBody) => api.POST(`${BASE}/types`, { body }),
    onSuccess: invalidate,
    meta: { suppressErrorToast: true },
  })
}

export function useUpdateWirType() {
  const invalidate = useInvalidateTypes()
  return useMutation({
    mutationFn: ({ id, body }: { id: string; body: WirTypeBody }) =>
      api.PUT(`${BASE}/types/${id}`, { body }),
    onSuccess: invalidate,
    meta: { suppressErrorToast: true },
  })
}

export function useDeleteWirType() {
  const invalidate = useInvalidateTypes()
  return useMutation({
    mutationFn: (id: string) => api.DELETE(`${BASE}/types/${id}`),
    onSuccess: invalidate,
  })
}
