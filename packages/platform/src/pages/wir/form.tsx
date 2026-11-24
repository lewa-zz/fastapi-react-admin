/*新增 / 编辑抽屉（react-hook-form + zod）*/
import * as React from "react"
import { useTranslation } from "react-i18next"
import { useForm } from "react-hook-form"
import { zodResolver } from "@hookform/resolvers/zod"
import { z } from "zod"
import { useQuery } from "@tanstack/react-query"
import { IconLoader2 } from "@tabler/icons-react"

import { Button } from "@admin/ui/components/button"
import { DateTimeValuePicker } from "@admin/ui/components/datetime-picker"
import { Input } from "@admin/ui/components/input"
import { QueryError } from "@admin/ui/components/query-error"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@admin/ui/components/select"
import {
  Sheet,
  SheetClose,
  SheetContent,
  SheetDescription,
  SheetFooter,
  SheetHeader,
  SheetTitle,
} from "@admin/ui/components/sheet"
import { Textarea } from "@admin/ui/components/textarea"

import { ApiError } from "../../api-client/errors"
import { useFieldError } from "../_shared/form-error"
import { FormField } from "../_shared/form-fields"
import { toWallTime, wallTimeToIso } from "../_shared/wall-time"
import {
  useCreateWirRecord,
  useUpdateWirRecord,
  wirTypesQuery,
  type WirRecord,
  type WirRecordBody,
} from "./api"

// 长度和后端列一致（`UniversalStr` 的 n）；后端 `ColumnLengthChecked` 才是权威，这里只为当场报错
const schema = z.object({
  type_id: z.string(),
  dc: z.string().max(32),
  discipline: z.string().max(16),
  doc_status: z.string().max(64),
  from_party: z.string().max(64),
  tml_no: z.string().max(128),
  pmweb_no: z.string().max(256),
  doc_type: z.string().max(16),
  description: z.string(),
  another_desc: z.string().max(512),
  filepath: z.string().max(1024),
  comment: z.string(),
  drt_submitted: z.string(),
  pmx_submitted: z.string(),
  cb_inspection: z.string(),
})
type Values = z.infer<typeof schema>

const EMPTY: Values = {
  type_id: "",
  dc: "",
  discipline: "",
  doc_status: "",
  from_party: "",
  tml_no: "",
  pmweb_no: "",
  doc_type: "",
  description: "",
  another_desc: "",
  filepath: "",
  comment: "",
  drt_submitted: "",
  pmx_submitted: "",
  cb_inspection: "",
}

const NONE = "__none__"
const asDate = (at: string | null | undefined) =>
  toWallTime(at)?.slice(0, 10) ?? ""
const toIso = (date: string) =>
  wallTimeToIso(date ? `${date} 00:00:00` : undefined)

const DISCIPLINES = ["BMS", "SEC", "ELV"]
const DOC_STATUS = ["Approved", "Approved as Noted", "Rejected", "Pending"]

export function WirRecordFormSheet({
  open,
  onOpenChange,
  editing,
}: {
  open: boolean
  onOpenChange: (o: boolean) => void
  editing: WirRecord | null
}) {
  const { t } = useTranslation()
  const fe = useFieldError()
  const create = useCreateWirRecord()
  const update = useUpdateWirRecord()
  const types = useQuery(wirTypesQuery)
  const [err, setErr] = React.useState<string | null>(null)
  const form = useForm<Values>({
    resolver: zodResolver(schema) as never,
    defaultValues: EMPTY,
  })

  React.useEffect(() => {
    if (!open) return
    setErr(null)
    form.reset(
      editing
        ? {
            type_id: editing.type_id ?? NONE,
            dc: editing.dc ?? "",
            discipline: editing.discipline ?? "",
            doc_status: editing.doc_status ?? "",
            from_party: editing.from_party ?? "",
            tml_no: editing.tml_no ?? "",
            pmweb_no: editing.pmweb_no ?? "",
            doc_type: editing.doc_type ?? "",
            description: editing.description ?? "",
            another_desc: editing.another_desc ?? "",
            filepath: editing.filepath ?? "",
            comment: editing.comment ?? "",
            drt_submitted: asDate(editing.drt_submitted),
            pmx_submitted: asDate(editing.pmx_submitted),
            cb_inspection: asDate(editing.cb_inspection),
          }
        : EMPTY
    )
  }, [open, editing, form])

  const typeItems = React.useMemo(() => {
    const items: Record<string, string> = { [NONE]: t("不指定") }
    for (const item of types.data ?? []) {
      items[item.id] = `${item.type_cn} / ${item.type_en}`
    }
    return items
  }, [types.data, t])

  const errs = form.formState.errors
  const pending = create.isPending || update.isPending

  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent side="right" className="data-[side=right]:sm:max-w-2xl">
        <SheetHeader>
          <SheetTitle>
            {editing ? t("编辑 WIR 记录") : t("新增 WIR 记录")}
          </SheetTitle>
          <SheetDescription>
            {t("一份 WIR 提交 / 批复记录一行。日期只到天，时间按 00:00 存。")}
          </SheetDescription>
        </SheetHeader>

        <form
          onSubmit={form.handleSubmit(async (v) => {
            setErr(null)
            const body: WirRecordBody = {
              type_id: v.type_id === NONE || !v.type_id ? null : v.type_id,
              dc: v.dc.trim() || null,
              discipline: v.discipline.trim() || null,
              doc_status: v.doc_status.trim() || null,
              from_party: v.from_party.trim() || null,
              tml_no: v.tml_no.trim() || null,
              pmweb_no: v.pmweb_no.trim() || null,
              doc_type: v.doc_type.trim() || null,
              description: v.description.trim() || null,
              another_desc: v.another_desc.trim() || null,
              filepath: v.filepath.trim() || null,
              comment: v.comment.trim() || null,
              drt_submitted: toIso(v.drt_submitted),
              pmx_submitted: toIso(v.pmx_submitted),
              cb_inspection: toIso(v.cb_inspection),
            }
            try {
              if (editing) await update.mutateAsync({ id: editing.id, body })
              else await create.mutateAsync(body)
              onOpenChange(false)
            } catch (e) {
              setErr(e instanceof ApiError ? e.message : t("保存失败"))
            }
          })}
          className="flex flex-1 flex-col overflow-hidden"
        >
          <div className="flex flex-1 flex-col gap-4 overflow-y-auto px-4 py-2">
            {types.isError && (
              <QueryError
                error={types.error}
                onRetry={() => void types.refetch()}
                title={t("类型列表加载失败")}
              />
            )}

            <div className="grid gap-4 sm:grid-cols-2">
              <FormField label={t("类型")}>
                <Select
                  value={form.watch("type_id") || NONE}
                  items={typeItems}
                  onValueChange={(v) =>
                    form.setValue("type_id", v ?? NONE, { shouldDirty: true })
                  }
                >
                  <SelectTrigger className="w-full">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {Object.entries(typeItems).map(([value, label]) => (
                      <SelectItem key={value} value={value}>
                        {label}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </FormField>
              <FormField label={t("所属 DC")} error={fe(errs.dc?.message)}>
                <Input
                  {...form.register("dc")}
                  placeholder="DC1-Fitout"
                  autoComplete="off"
                />
              </FormField>
              <FormField
                label={t("专业")}
                hint={t("常用：{{list}}", { list: DISCIPLINES.join(" / ") })}
                error={fe(errs.discipline?.message)}
              >
                <Input {...form.register("discipline")} autoComplete="off" />
              </FormField>
              <FormField
                label={t("批复状态")}
                hint={t("常用：{{list}}", { list: DOC_STATUS.join(" / ") })}
                error={fe(errs.doc_status?.message)}
              >
                <Input {...form.register("doc_status")} autoComplete="off" />
              </FormField>
              <FormField
                label={t("提交方")}
                error={fe(errs.from_party?.message)}
              >
                <Input {...form.register("from_party")} autoComplete="off" />
              </FormField>
              <FormField
                label={t("文件类型")}
                error={fe(errs.doc_type?.message)}
              >
                <Input
                  {...form.register("doc_type")}
                  placeholder="WIR / MIR"
                  autoComplete="off"
                />
              </FormField>
            </div>

            <div className="grid gap-4 sm:grid-cols-2">
              <FormField label={t("TML 编号")} error={fe(errs.tml_no?.message)}>
                <Input {...form.register("tml_no")} autoComplete="off" />
              </FormField>
              <FormField
                label={t("PMWeb 编号")}
                error={fe(errs.pmweb_no?.message)}
              >
                <Input {...form.register("pmweb_no")} autoComplete="off" />
              </FormField>
            </div>

            <FormField
              label={t("检查内容")}
              error={fe(errs.description?.message)}
            >
              <Textarea rows={3} {...form.register("description")} />
            </FormField>

            <div className="grid gap-4 sm:grid-cols-3">
              <FormField label={t("DRT 提交日期")}>
                <DateTimeValuePicker
                  value={form.watch("drt_submitted") || undefined}
                  onChange={(v) =>
                    form.setValue("drt_submitted", v ?? "", {
                      shouldDirty: true,
                    })
                  }
                  aria-label={t("DRT 提交日期")}
                />
              </FormField>
              <FormField label={t("PMX 提交日期")}>
                <DateTimeValuePicker
                  value={form.watch("pmx_submitted") || undefined}
                  onChange={(v) =>
                    form.setValue("pmx_submitted", v ?? "", {
                      shouldDirty: true,
                    })
                  }
                  aria-label={t("PMX 提交日期")}
                />
              </FormField>
              <FormField label={t("C&B 检查日期")}>
                <DateTimeValuePicker
                  value={form.watch("cb_inspection") || undefined}
                  onChange={(v) =>
                    form.setValue("cb_inspection", v ?? "", {
                      shouldDirty: true,
                    })
                  }
                  aria-label={t("C&B 检查日期")}
                />
              </FormField>
            </div>

            <FormField
              label={t("别称 / 中文描述")}
              error={fe(errs.another_desc?.message)}
            >
              <Input {...form.register("another_desc")} autoComplete="off" />
            </FormField>
            <FormField
              label={t("签字件路径")}
              error={fe(errs.filepath?.message)}
            >
              <Textarea rows={2} {...form.register("filepath")} />
            </FormField>
            <FormField label={t("顾问意见")} error={fe(errs.comment?.message)}>
              <Textarea rows={4} {...form.register("comment")} />
            </FormField>

            {err && <p className="text-sm text-destructive">{err}</p>}
          </div>

          <SheetFooter>
            <Button type="submit" disabled={pending}>
              {pending && <IconLoader2 className="size-4 animate-spin" />}
              {editing ? t("保存修改") : t("创建记录")}
            </Button>
            <SheetClose render={<Button variant="outline" type="button" />}>
              {t("取消")}
            </SheetClose>
          </SheetFooter>
        </form>
      </SheetContent>
    </Sheet>
  )
}
