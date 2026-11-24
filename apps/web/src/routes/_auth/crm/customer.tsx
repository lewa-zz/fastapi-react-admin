import { createFileRoute } from "@tanstack/react-router"
import { z } from "zod"

import { requirePerm } from "@admin/platform/auth/guards"

const searchSchema = z.object({
  page: z.coerce.number().int().min(1).optional(),
  size: z.coerce.number().int().min(1).optional(),
  /** 摆开但还没填值的格子 */
  f: z.string().optional(),
  name: z.string().optional(),
  phone: z.string().optional(),
  level: z.coerce.number().int().optional(),
  status: z.coerce.number().int().optional(),
})

/** 页面由 TabOutlet 挂载；这里只声明 search schema / staticData / 权限（硬纪律 3） */
export const Route = createFileRoute("/_auth/crm/customer")({
  validateSearch: searchSchema,
  beforeLoad: requirePerm("crm:customer:list"),
  staticData: { title: "客户管理" },
  component: () => null,
})
