/*新增 / 编辑抽屉（react-hook-form + zod）*/
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
import { Switch } from "@admin/ui/components/switch"
import { Textarea } from "@admin/ui/components/textarea"

import { ApiError } from "../../api-client/errors"
import { useFieldError } from "../_shared/form-error"
import { FormField } from "../_shared/form-fields"
import {
  useCreateMaterial,
  useUpdateMaterial,
  type Material,
  type MaterialBody,
} from "./api"

/**
 * `kind` 的取值来自源 Excel 的 `type` 列，**原样存整串**（含全角括号）：
 * 库里的值是 `Program（编程/软件）`，筛选 / 展示都按它相等匹配，
 * 缩写一个 `Program` 会让筛选一条都查不到。
 */
export const KIND_OPTIONS = [
  { value: "PLC", label: "PLC" },
  { value: "Program（编程/软件）", label: "Program（编程/软件）" },
  { value: "Sensor（现场安装）", label: "Sensor（现场安装）" },
] as const

/** 纯数字（可空）。后端是 `Numeric(14,4)`，空串要变成 null 而不是 0 */
const NUM_RE = /^\d*(\.\d+)?$/

// 长度和后端列一致（`UniversalStr` 的 n）；后端 `ColumnLengthChecked` 才是权威，这里只为当场报错
const schema = z.object({
  // 来源 Excel 行 ID：手工新增留空，编辑时改它才会撞后端的唯一约束（409）
  source_id: z.string().regex(/^\d*$/, "请输入整数").max(19),
  kind: z.string().min(1, "请选择类型"),
  category: z.string().trim().min(1, "请输入类别").max(64),
  name_cn: z.string().trim().min(1, "请输入中文名").max(128),
  name_en: z.string().trim().min(1, "请输入英文名").max(256),
  model: z.string().max(64),
  spec: z.string(),
  brand: z.string().max(64),
  qty: z.string().regex(NUM_RE, "请输入数字"),
  unit: z.string().trim().min(1, "请输入单位").max(32),
  price: z.string().regex(NUM_RE, "请输入数字"),
  contract_price: z.string().regex(NUM_RE, "请输入数字"),
  in_price: z.string().regex(NUM_RE, "请输入数字"),
  out_price: z.string().regex(NUM_RE, "请输入数字"),
  market_price: z.string().regex(NUM_RE, "请输入数字"),
  memo: z.string().max(256),
  source: z.string().max(128),
  currency: z.string().trim().min(1, "请输入币种").max(8),
  active: z.boolean(),
})
type Values = z.infer<typeof schema>

const EMPTY: Values = {
  source_id: "",
  kind: "",
  category: "",
  name_cn: "",
  name_en: "",
  model: "",
  spec: "",
  brand: "",
  qty: "",
  unit: "台/件",
  price: "",
  contract_price: "",
  in_price: "",
  out_price: "",
  market_price: "",
  memo: "",
  source: "",
  currency: "RMB",
  active: true,
}

/** `Decimal(14,4)` 出网可能是 `"12.5000"`，也可能已经是数字 —— 回显统一转成文本 */
const asText = (v: number | string | null | undefined) =>
  v === null || v === undefined ? "" : String(v)

/** 表单里是字符串：空 = 不填（null），否则转数字 */
const asNum = (s: string) => (s.trim() === "" ? null : Number(s))
const asInt = (s: string) => (s.trim() === "" ? null : Number.parseInt(s, 10))

export function MaterialFormSheet({
  open,
  onOpenChange,
  editing,
}: {
  open: boolean
  onOpenChange: (o: boolean) => void
  editing: Material | null
}) {
  const { t } = useTranslation()
  const fe = useFieldError()
  const create = useCreateMaterial()
  const update = useUpdateMaterial()
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
            source_id: asText(editing.source_id),
            kind: editing.kind ?? "",
            category: editing.category ?? "",
            name_cn: editing.name_cn ?? "",
            name_en: editing.name_en ?? "",
            model: editing.model ?? "",
            spec: editing.spec ?? "",
            brand: editing.brand ?? "",
            qty: asText(editing.qty),
            unit: editing.unit || "台/件",
            price: asText(editing.price),
            contract_price: asText(editing.contract_price),
            in_price: asText(editing.in_price),
            out_price: asText(editing.out_price),
            market_price: asText(editing.market_price),
            memo: editing.memo ?? "",
            source: editing.source ?? "",
            currency: editing.currency || "RMB",
            active: editing.active,
          }
        : EMPTY
    )
  }, [open, editing, form])

  /**
   * 类型下拉的选项要**并上当前值**：库里已经存着 Excel 原样的一串
   * （`Program（编程/软件）`）或者别人手工填过的第三种，选项里没有它的话
   * 编辑一打开，关闭态是空的 —— 用户会以为这条材料没有类型。
   */
  const kindItems = React.useMemo(() => {
    const items: Record<string, string> = {}
    for (const item of KIND_OPTIONS) items[item.value] = item.label
    const current = editing?.kind
    if (current && !items[current]) items[current] = current
    return items
  }, [editing?.kind])

  const errs = form.formState.errors
  const pending = create.isPending || update.isPending

  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent side="right" className="data-[side=right]:sm:max-w-2xl">
        <SheetHeader>
          <SheetTitle>
            {editing ? t("编辑材料") : t("新增材料")}
          </SheetTitle>
          <SheetDescription>
            {t(
              "一种材料一行。金额按合同口径填，停用的材料不会出现在候选里。"
            )}
          </SheetDescription>
        </SheetHeader>

        <form
          onSubmit={form.handleSubmit(async (v) => {
            setErr(null)
            const body: MaterialBody = {
              source_id: asInt(v.source_id),
              kind: v.kind,
              category: v.category.trim(),
              name_cn: v.name_cn.trim(),
              name_en: v.name_en.trim(),
              model: v.model.trim() || null,
              spec: v.spec.trim() || null,
              brand: v.brand.trim() || null,
              qty: asNum(v.qty),
              unit: v.unit.trim(),
              price: asNum(v.price),
              contract_price: asNum(v.contract_price),
              in_price: asNum(v.in_price),
              out_price: asNum(v.out_price),
              market_price: asNum(v.market_price),
              memo: v.memo.trim() || null,
              source: v.source.trim() || null,
              currency: v.currency.trim(),
              active: v.active,
            }
            try {
              if (editing) await update.mutateAsync({ id: editing.id, body })
              else await create.mutateAsync(body)
              onOpenChange(false)
            } catch (e) {
              // 来源 ID 是导入幂等键，撞了后端给 409 —— 把原话换成一句能直接照做的
              setErr(
                e instanceof ApiError && e.httpStatus === 409
                  ? t("来源 ID 已存在")
                  : e instanceof ApiError
                    ? e.message
                    : t("保存失败")
              )
            }
          })}
          className="flex flex-1 flex-col overflow-hidden"
        >
          <div className="flex flex-1 flex-col gap-4 overflow-y-auto overflow-x-hidden px-4 py-2">
            <div className="grid gap-4 sm:grid-cols-2">
              <FormField
                label={t("类型")}
                error={fe(errs.kind?.message)}
                required
              >
                <Select
                  value={form.watch("kind")}
                  items={kindItems}
                  onValueChange={(v) =>
                    form.setValue("kind", v ?? "", { shouldDirty: true })
                  }
                >
                  <SelectTrigger className="w-full">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {Object.entries(kindItems).map(([value, label]) => (
                      <SelectItem key={value} value={value}>
                        {label}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </FormField>
              <FormField
                label={t("类别")}
                hint={t("源表的长文本类别，如「BMS控制柜」")}
                error={fe(errs.category?.message)}
                required
              >
                <Input {...form.register("category")} autoComplete="off" />
              </FormField>
              <FormField
                label={t("中文名")}
                error={fe(errs.name_cn?.message)}
                required
              >
                <Input {...form.register("name_cn")} autoComplete="off" />
              </FormField>
              <FormField
                label={t("英文名")}
                error={fe(errs.name_en?.message)}
                required
              >
                <Input {...form.register("name_en")} autoComplete="off" />
              </FormField>
              <FormField label={t("型号")} error={fe(errs.model?.message)}>
                <Input {...form.register("model")} autoComplete="off" />
              </FormField>
              <FormField label={t("品牌")} error={fe(errs.brand?.message)}>
                <Input {...form.register("brand")} autoComplete="off" />
              </FormField>
            </div>

            <FormField
              label={t("规格")}
              hint={t("源表里含换行，可多行填写")}
              error={fe(errs.spec?.message)}
            >
              <Textarea rows={4} {...form.register("spec")} />
            </FormField>

            <div className="grid gap-4 sm:grid-cols-3">
              <FormField label={t("数量")} error={fe(errs.qty?.message)}>
                <Input
                  {...form.register("qty")}
                  inputMode="decimal"
                  autoComplete="off"
                />
              </FormField>
              <FormField
                label={t("单位")}
                error={fe(errs.unit?.message)}
                required
              >
                <Input {...form.register("unit")} autoComplete="off" />
              </FormField>
              <FormField label={t("币种")} error={fe(errs.currency?.message)}>
                <Input {...form.register("currency")} autoComplete="off" />
              </FormField>
            </div>

            <div className="grid gap-4 sm:grid-cols-3">
              <FormField
                label={t("合同单价")}
                error={fe(errs.price?.message)}
              >
                <Input
                  {...form.register("price")}
                  inputMode="decimal"
                  autoComplete="off"
                />
              </FormField>
              <FormField
                label={t("合同合价")}
                error={fe(errs.contract_price?.message)}
              >
                <Input
                  {...form.register("contract_price")}
                  inputMode="decimal"
                  autoComplete="off"
                />
              </FormField>
              <FormField
                label={t("报入单价")}
                error={fe(errs.in_price?.message)}
              >
                <Input
                  {...form.register("in_price")}
                  inputMode="decimal"
                  autoComplete="off"
                />
              </FormField>
              <FormField
                label={t("报出价")}
                error={fe(errs.out_price?.message)}
              >
                <Input
                  {...form.register("out_price")}
                  inputMode="decimal"
                  autoComplete="off"
                />
              </FormField>
              <FormField
                label={t("市场价")}
                error={fe(errs.market_price?.message)}
              >
                <Input
                  {...form.register("market_price")}
                  inputMode="decimal"
                  autoComplete="off"
                />
              </FormField>
            </div>

            <div className="grid gap-4 sm:grid-cols-2">
              <FormField label={t("备注")} error={fe(errs.memo?.message)}>
                <Input {...form.register("memo")} autoComplete="off" />
              </FormField>
              <FormField label={t("来源")} error={fe(errs.source?.message)}>
                <Input {...form.register("source")} autoComplete="off" />
              </FormField>
              <FormField
                label={t("来源 ID")}
                hint={t("源 Excel 的行号；手工新增留空")}
                error={fe(errs.source_id?.message)}
              >
                <Input
                  {...form.register("source_id")}
                  inputMode="numeric"
                  placeholder={t("不填")}
                  autoComplete="off"
                />
              </FormField>
              <FormField
                label={t("启用")}
                hint={t("停用的材料不进候选，但记录还在")}
              >
                <Switch
                  checked={form.watch("active")}
                  onCheckedChange={(v) =>
                    form.setValue("active", Boolean(v), { shouldDirty: true })
                  }
                />
              </FormField>
            </div>

            {err && <p className="text-sm text-destructive">{err}</p>}
          </div>

          <SheetFooter>
            <Button type="submit" disabled={pending}>
              {pending && <IconLoader2 className="size-4 animate-spin" />}
              {editing ? t("保存修改") : t("创建材料")}
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
