/*新增,编辑抽屉（react-hook-form + zod）*/
import * as React from "react"
import { useTranslation } from "react-i18next"
import { useForm } from "react-hook-form"
import { zodResolver } from "@hookform/resolvers/zod"
import { z } from "zod"
import { IconLoader2 } from "@tabler/icons-react"

import { Button } from "@admin/ui/components/button"
import { Input } from "@admin/ui/components/input"
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
import { STATUS_FORM_ITEMS } from "../_shared/status"
import {
  CUSTOMER_LEVEL_LABEL,
  useCreateCustomer,
  useUpdateCustomer,
  type Customer,
} from "./api"

// 长度和后端列一致（name 64 / phone 20）；后端的 ColumnLengthChecked 才是权威，这里只为当场报错
const schema = z.object({
  name: z.string().trim().min(1, "请输入客户名称").max(64),
  phone: z.string().max(20).optional(),
  level: z.number().int().min(0).max(2),
  status: z.number().int(),
  remark: z.string().max(500).optional(),
})
type Values = z.infer<typeof schema>

const EMPTY: Values = { name: "", phone: "", level: 0, status: 1, remark: "" }

export function CustomerFormSheet({
  open,
  onOpenChange,
  editing,
}: {
  open: boolean
  onOpenChange: (o: boolean) => void
  editing: Customer | null
}) {
  const { t } = useTranslation()
  const fe = useFieldError()
  const create = useCreateCustomer()
  const update = useUpdateCustomer()
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
            name: editing.name,
            phone: editing.phone ?? "",
            level: editing.level,
            status: editing.status,
            remark: editing.remark ?? "",
          }
        : EMPTY
    )
  }, [open, editing, form])

  const levelItems = React.useMemo(
    () =>
      Object.fromEntries(
        Object.entries(CUSTOMER_LEVEL_LABEL).map(([v, l]) => [v, t(l)])
      ),
    [t]
  )
  const statusItems = React.useMemo(
    () =>
      Object.fromEntries(
        Object.entries(STATUS_FORM_ITEMS).map(([v, l]) => [v, t(l)])
      ),
    [t]
  )
  const errs = form.formState.errors
  const pending = create.isPending || update.isPending

  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent side="right" className="data-[side=right]:sm:max-w-md">
        <SheetHeader>
          <SheetTitle>{editing ? t("编辑客户") : t("新增客户")}</SheetTitle>
          <SheetDescription>
            {t("新建的客户归属到你所在的部门，负责人默认是你。")}
          </SheetDescription>
        </SheetHeader>
        <form
          onSubmit={form.handleSubmit(async (v) => {
            setErr(null)
            const body = {
              name: v.name,
              phone: v.phone?.trim() || null,
              level: v.level,
              status: v.status,
              remark: v.remark?.trim() || null,
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
            <FormField
              label={t("客户名称")}
              error={fe(errs.name?.message)}
              required
            >
              <Input {...form.register("name")} autoComplete="off" />
            </FormField>
            <FormField label={t("联系电话")} error={fe(errs.phone?.message)}>
              <Input {...form.register("phone")} autoComplete="off" />
            </FormField>
            <div className="grid grid-cols-2 gap-4">
              <FormField label={t("等级")} required>
                <Select
                  value={String(form.watch("level"))}
                  items={levelItems}
                  onValueChange={(v) =>
                    form.setValue("level", Number(v), { shouldValidate: true })
                  }
                >
                  <SelectTrigger className="w-full">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {Object.entries(levelItems).map(([v, l]) => (
                      <SelectItem key={v} value={v}>
                        {l}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </FormField>
              <FormField label={t("状态")} required>
                <Select
                  value={String(form.watch("status"))}
                  items={statusItems}
                  onValueChange={(v) =>
                    form.setValue("status", Number(v), { shouldValidate: true })
                  }
                >
                  <SelectTrigger className="w-full">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {Object.entries(statusItems).map(([v, l]) => (
                      <SelectItem key={v} value={v}>
                        {l}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </FormField>
            </div>
            <FormField label={t("备注")} error={fe(errs.remark?.message)}>
              <Textarea rows={3} {...form.register("remark")} />
            </FormField>
            {err && <p className="text-sm text-destructive">{err}</p>}
          </div>
          <SheetFooter>
            <Button type="submit" disabled={pending}>
              {pending && <IconLoader2 className="size-4 animate-spin" />}
              {editing ? t("保存修改") : t("创建客户")}
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
