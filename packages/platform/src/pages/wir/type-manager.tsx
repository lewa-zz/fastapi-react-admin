/* WIR 类型管理抽屉：列表 + 新增 / 编辑 / 删除 + 从 Excel 导入类型 */
import * as React from "react"
import { useTranslation } from "react-i18next"
import { useQuery } from "@tanstack/react-query"
import {
  IconLoader2,
  IconPencil,
  IconPlus,
  IconTrash,
  IconUpload,
} from "@tabler/icons-react"

import { Button } from "@admin/ui/components/button"
import { Input } from "@admin/ui/components/input"
import { QueryError } from "@admin/ui/components/query-error"
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
} from "@admin/ui/components/sheet"

import { ApiError } from "../../api-client/errors"
import { Can } from "../../auth/can"
import { ConfirmDialog } from "../../shell/confirm-dialog"
import { ImportSheet } from "../_shared/data-io/import-sheet"
import {
  useCreateWirType,
  useDeleteWirType,
  useUpdateWirType,
  wirKeys,
  wirTypesQuery,
  type WirType,
} from "./api"

export function WirTypeManager({
  open,
  onOpenChange,
}: {
  open: boolean
  onOpenChange: (o: boolean) => void
}) {
  const { t } = useTranslation()
  const types = useQuery(wirTypesQuery)
  const create = useCreateWirType()
  const update = useUpdateWirType()
  const del = useDeleteWirType()

  const [editing, setEditing] = React.useState<WirType | null>(null)
  const [typeCn, setTypeCn] = React.useState("")
  const [typeEn, setTypeEn] = React.useState("")
  const [err, setErr] = React.useState<string | null>(null)
  const [pendingDelete, setPendingDelete] = React.useState<WirType | null>(null)
  const [importOpen, setImportOpen] = React.useState(false)

  React.useEffect(() => {
    if (!open) {
      setEditing(null)
      setTypeCn("")
      setTypeEn("")
      setErr(null)
      setImportOpen(false)
    }
  }, [open])

  const resetForm = React.useCallback(() => {
    setEditing(null)
    setTypeCn("")
    setTypeEn("")
    setErr(null)
  }, [])

  const startEdit = (item: WirType) => {
    setEditing(item)
    setTypeCn(item.type_cn)
    setTypeEn(item.type_en)
    setErr(null)
  }

  const pending = create.isPending || update.isPending
  const canSubmit = typeCn.trim() !== "" && typeEn.trim() !== ""

  const submit = async () => {
    if (!canSubmit) return
    setErr(null)
    const body = { type_cn: typeCn.trim(), type_en: typeEn.trim() }
    try {
      if (editing) await update.mutateAsync({ id: editing.id, body })
      else await create.mutateAsync(body)
      resetForm()
    } catch (e) {
      setErr(e instanceof ApiError ? e.message : t("保存失败"))
    }
  }

  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent side="right" className="data-[side=right]:sm:max-w-lg">
        <SheetHeader>
          <SheetTitle>{t("WIR 类型")}</SheetTitle>
          <SheetDescription>
            {t(
              "类型是台账的中英对照参考数据。Excel 导入台账之前先导入类型表。"
            )}
          </SheetDescription>
        </SheetHeader>

        <div className="flex min-h-0 flex-1 flex-col gap-4 px-4">
          <div className="flex flex-col gap-2 rounded-md border p-3">
            <div className="grid gap-2 sm:grid-cols-2">
              <Input
                value={typeCn}
                onChange={(e) => setTypeCn(e.target.value)}
                placeholder={t("类型中文名")}
                aria-label={t("类型中文名")}
                autoComplete="off"
              />
              <Input
                value={typeEn}
                onChange={(e) => setTypeEn(e.target.value)}
                placeholder={t("类型英文名")}
                aria-label={t("类型英文名")}
                autoComplete="off"
              />
            </div>
            <div className="flex flex-wrap items-center gap-2">
              <Can perm={editing ? "wir:type:edit" : "wir:type:add"}>
                <Button
                  size="sm"
                  disabled={!canSubmit || pending}
                  onClick={() => void submit()}
                >
                  {pending ? (
                    <IconLoader2 className="size-4 animate-spin" />
                  ) : (
                    <IconPlus className="size-4" />
                  )}
                  {editing ? t("保存修改") : t("新增类型")}
                </Button>
              </Can>
              {editing && (
                <Button size="sm" variant="outline" onClick={resetForm}>
                  {t("取消编辑")}
                </Button>
              )}
              <Can perm="wir:import">
                <Button
                  size="sm"
                  variant="outline"
                  onClick={() => setImportOpen(true)}
                >
                  <IconUpload className="size-4" />
                  {t("导入类型")}
                </Button>
              </Can>
            </div>
            {err && <p className="text-sm text-destructive">{err}</p>}
          </div>

          <div className="flex min-h-0 flex-1 flex-col gap-2 overflow-y-auto">
            {types.isError ? (
              <QueryError
                error={types.error}
                onRetry={() => void types.refetch()}
                title={t("类型列表加载失败")}
              />
            ) : (types.data ?? []).length === 0 ? (
              <p className="text-sm text-muted-foreground">
                {types.isPending ? t("加载中…") : t("还没有 WIR 类型")}
              </p>
            ) : (
              (types.data ?? []).map((item) => (
                <div
                  key={item.id}
                  className="flex items-center gap-2 rounded-md border px-3 py-2"
                >
                  <div className="min-w-0 flex-1">
                    <p className="truncate text-sm font-medium">
                      {item.type_cn}
                    </p>
                    <p className="truncate text-xs text-muted-foreground">
                      {item.type_en}
                    </p>
                  </div>
                  <Can perm="wir:type:edit">
                    <Button
                      size="icon"
                      variant="ghost"
                      className="size-7"
                      aria-label={t("编辑 {{name}}", { name: item.type_cn })}
                      onClick={() => startEdit(item)}
                    >
                      <IconPencil className="size-4" />
                    </Button>
                  </Can>
                  <Can perm="wir:type:del">
                    <Button
                      size="icon"
                      variant="ghost"
                      className="size-7 text-destructive"
                      aria-label={t("删除 {{name}}", { name: item.type_cn })}
                      onClick={() => setPendingDelete(item)}
                    >
                      <IconTrash className="size-4" />
                    </Button>
                  </Can>
                </div>
              ))
            )}
          </div>
        </div>

        <ImportSheet
          open={importOpen}
          onOpenChange={setImportOpen}
          base="/api/v1/sys/wir/types/import"
          title={t("导入 WIR 类型")}
          description={t(
            "支持原始文件的 type 表，也支持下载模板填写。导入后类型 ID 会保留文件里的原值。"
          )}
          invalidate={wirKeys.types}
          modes={["create", "upsert"]}
          previewKeys={["source_id", "type_cn", "type_en"]}
          testId="wir-type-import-sheet"
        />

        <ConfirmDialog
          open={pendingDelete !== null}
          onOpenChange={(o) => !o && setPendingDelete(null)}
          title={t("删除 WIR 类型")}
          description={
            pendingDelete
              ? t(
                  "确定删除「{{name}}」吗？还有记录在用这个类型时后端会拒绝。",
                  {
                    name: pendingDelete.type_cn,
                  }
                )
              : ""
          }
          confirmText={t("删除")}
          destructive
          pending={del.isPending}
          onConfirm={async () => {
            if (!pendingDelete) return
            try {
              await del.mutateAsync(pendingDelete.id)
              if (editing?.id === pendingDelete.id) resetForm()
            } finally {
              setPendingDelete(null)
            }
          }}
        />
      </SheetContent>
    </Sheet>
  )
}
