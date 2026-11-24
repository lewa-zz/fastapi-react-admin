import { createFileRoute } from "@tanstack/react-router"
import { z } from "zod"

import { requirePerm } from "@admin/platform/auth/guards"

const searchSchema = z.object({
  page: z.coerce.number().int().min(1).optional(),
  size: z.coerce.number().int().min(1).optional(),
  /** 摆开但还没填值的格子 */
  f: z.string().optional(),
  search: z.string().optional(),
  dc: z.string().optional(),
  discipline: z.string().optional(),
  doc_status: z.string().optional(),
  /** 雪花 ID 保持字符串（硬纪律 6），不要 `z.coerce.number()` */
  type_id: z.string().optional(),
})

/** 页面由 TabOutlet 挂载；这里只声明 search schema / staticData / 权限（硬纪律 3） */
export const Route = createFileRoute("/_auth/project/wir")({
  validateSearch: searchSchema,
  beforeLoad: requirePerm("wir:record:list"),
  staticData: { title: "WIR 台账" },
  component: () => null,
})
