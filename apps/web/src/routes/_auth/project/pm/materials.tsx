import { createFileRoute } from "@tanstack/react-router"
import { z } from "zod"

import { requirePerm } from "@admin/platform/auth/guards"

const searchSchema = z.object({
  page: z.coerce.number().int().min(1).optional(),
  size: z.coerce.number().int().min(1).optional(),
  /** 摆开但还没填值的格子 */
  f: z.string().optional(),
  kind: z.string().optional(),
  category: z.string().optional(),
  brand: z.string().optional(),
  /** 「启用」是 boolean 字段，但 URL 里只能是字符串（QueryBar 出参时再转回 boolean） */
  active: z.string().optional(),
  search: z.string().optional(),
})

/** 页面由 TabOutlet 挂载；这里只声明 search schema / staticData / 权限（硬纪律 3） */
export const Route = createFileRoute("/_auth/project/pm/materials")({
  validateSearch: searchSchema,
  beforeLoad: requirePerm("pm:material:list"),
  staticData: { title: "材料" },
  component: () => null,
})
