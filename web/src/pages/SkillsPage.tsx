import { useEffect, useLayoutEffect, useState, useMemo, useCallback } from "react";
import {
  Package,
  Search,
  Wrench,
  X,
  Cpu,
  Globe,
  Shield,
  Eye,
  Paintbrush,
  Brain,
  Blocks,
  Code,
  Zap,
  Filter,
  Plus,
  Save,
  Trash2,
  ArrowLeft,
  Copy,
  Lock,
} from "lucide-react";
import { api } from "@/lib/api";
import type { SkillInfo, SkillDetail, ToolsetInfo } from "@/lib/api";
import { useToast } from "@/hooks/useToast";
import { Toast } from "@/components/Toast";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { ConfirmDialog } from "@/components/ui/confirm-dialog";
import { Badge } from "@nous-research/ui/ui/components/badge";
import { Button } from "@nous-research/ui/ui/components/button";
import { ListItem } from "@nous-research/ui/ui/components/list-item";
import { Spinner } from "@nous-research/ui/ui/components/spinner";
import { Switch } from "@nous-research/ui/ui/components/switch";
import { cn } from "@/lib/utils";
import { Input } from "@/components/ui/input";
import { useI18n } from "@/i18n";
import { usePageHeader } from "@/contexts/usePageHeader";
import { PluginSlot } from "@/plugins";

/* ------------------------------------------------------------------ */
/*  Types & helpers                                                    */
/* ------------------------------------------------------------------ */

const CATEGORY_LABELS: Record<string, string> = {
  mlops: "MLOps",
  "mlops/cloud": "MLOps / Cloud",
  "mlops/evaluation": "MLOps / Evaluation",
  "mlops/inference": "MLOps / Inference",
  "mlops/models": "MLOps / Models",
  "mlops/training": "MLOps / Training",
  "mlops/vector-databases": "MLOps / Vector DBs",
  mcp: "MCP",
  "red-teaming": "Red Teaming",
  ocr: "OCR",
  p5js: "p5.js",
  ai: "AI",
  ux: "UX",
  ui: "UI",
};

function prettyCategory(
  raw: string | null | undefined,
  generalLabel: string,
): string {
  if (!raw) return generalLabel;
  if (CATEGORY_LABELS[raw]) return CATEGORY_LABELS[raw];
  return raw
    .split(/[-_/]/)
    .map((w) => w.charAt(0).toUpperCase() + w.slice(1))
    .join(" ");
}

const TOOLSET_ICONS: Record<
  string,
  React.ComponentType<{ className?: string }>
> = {
  computer: Cpu,
  web: Globe,
  security: Shield,
  vision: Eye,
  design: Paintbrush,
  ai: Brain,
  integration: Blocks,
  code: Code,
  automation: Zap,
};

function toolsetIcon(
  name: string,
): React.ComponentType<{ className?: string }> {
  const lower = name.toLowerCase();
  for (const [key, icon] of Object.entries(TOOLSET_ICONS)) {
    if (lower.includes(key)) return icon;
  }
  return Wrench;
}

/* ------------------------------------------------------------------ */
/*  Component                                                          */
/* ------------------------------------------------------------------ */

export default function SkillsPage() {
  const [skills, setSkills] = useState<SkillInfo[]>([]);
  const [toolsets, setToolsets] = useState<ToolsetInfo[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [view, setView] = useState<"skills" | "toolsets">("skills");
  const [activeCategory, setActiveCategory] = useState<string | null>(null);
  const [togglingSkills, setTogglingSkills] = useState<Set<string>>(new Set());
  const [selected, setSelected] = useState<SkillInfo | null>(null);
  const [detail, setDetail] = useState<SkillDetail | null>(null);
  const [detailLoading, setDetailLoading] = useState(false);
  const [editContent, setEditContent] = useState("");
  const [saving, setSaving] = useState(false);
  const [deleteOpen, setDeleteOpen] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const [showCreate, setShowCreate] = useState(false);
  const [createName, setCreateName] = useState("");
  const [createCategory, setCreateCategory] = useState("");
  const [createContent, setCreateContent] = useState(
    "---\nname: my-skill\ndescription: One-line description\n---\n\n# My skill\n\nWrite the skill instructions here.\n",
  );
  const [creating, setCreating] = useState(false);
  const { toast, showToast } = useToast();
  const { t } = useI18n();
  const { setAfterTitle, setEnd } = usePageHeader();

  const reloadSkills = useCallback(async () => {
    const s = await api.getSkills();
    setSkills(s);
    return s;
  }, []);

  useEffect(() => {
    Promise.all([api.getSkills(), api.getToolsets()])
      .then(([s, tsets]) => {
        setSkills(s);
        setToolsets(tsets);
      })
      .catch(() => showToast(t.common.loading, "error"))
      .finally(() => setLoading(false));
  }, []);

  /* ---- Toggle skill ---- */
  const handleToggleSkill = async (skill: SkillInfo) => {
    setTogglingSkills((prev) => new Set(prev).add(skill.name));
    try {
      await api.toggleSkill(skill.name, !skill.enabled);
      setSkills((prev) =>
        prev.map((s) =>
          s.name === skill.name ? { ...s, enabled: !s.enabled } : s,
        ),
      );
      showToast(
        `${skill.name} ${skill.enabled ? t.common.disabled : t.common.enabled}`,
        "success",
      );
    } catch {
      showToast(`${t.common.failedToToggle} ${skill.name}`, "error");
    } finally {
      setTogglingSkills((prev) => {
        const next = new Set(prev);
        next.delete(skill.name);
        return next;
      });
    }
  };

  /* ---- Detail / Edit / Delete / Create ---- */
  const openDetail = useCallback(
    async (skill: SkillInfo) => {
      setSelected(skill);
      setDetail(null);
      setDetailLoading(true);
      try {
        const d = await api.getSkill(skill.name);
        setDetail(d);
        setEditContent(d.content);
      } catch (err: unknown) {
        const msg = err instanceof Error ? err.message : String(err);
        showToast(`${t.skills.loadDetailFailed ?? "Load failed"}: ${msg}`, "error");
        setSelected(null);
      } finally {
        setDetailLoading(false);
      }
    },
    [showToast, t],
  );

  const closeDetail = useCallback(() => {
    setSelected(null);
    setDetail(null);
    setEditContent("");
    setSaving(false);
  }, []);

  const handleSave = useCallback(async () => {
    if (!detail) return;
    if (!editContent.trim()) {
      showToast(t.skills.contentRequired ?? "Content required", "error");
      return;
    }
    setSaving(true);
    try {
      await api.updateSkill(detail.name, editContent);
      showToast(t.skills.saved ?? "Saved", "success");
      const fresh = await api.getSkill(detail.name);
      setDetail(fresh);
      setEditContent(fresh.content);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : String(err);
      showToast(`${t.skills.saveFailed ?? "Save failed"}: ${msg}`, "error");
    } finally {
      setSaving(false);
    }
  }, [detail, editContent, showToast, t]);

  const handleDelete = useCallback(async () => {
    if (!detail) return;
    setDeleting(true);
    try {
      await api.deleteSkill(detail.name);
      showToast(t.skills.deleted ?? "Deleted", "success");
      setDeleteOpen(false);
      closeDetail();
      await reloadSkills();
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : String(err);
      showToast(`${t.skills.deleteFailed ?? "Delete failed"}: ${msg}`, "error");
    } finally {
      setDeleting(false);
    }
  }, [detail, closeDetail, reloadSkills, showToast, t]);

  const handleCloneToUser = useCallback(async () => {
    if (!detail) return;
    setSaving(true);
    try {
      await api.createSkill({
        name: detail.name,
        category: detail.category ?? undefined,
        content: editContent,
      });
      showToast(t.skills.skillCreated ?? "Skill created", "success");
      await reloadSkills();
      const fresh = await api.getSkill(detail.name);
      setDetail(fresh);
      setEditContent(fresh.content);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : String(err);
      showToast(`${t.skills.createFailed ?? "Create failed"}: ${msg}`, "error");
    } finally {
      setSaving(false);
    }
  }, [detail, editContent, reloadSkills, showToast, t]);

  const handleCreate = useCallback(async () => {
    const name = createName.trim();
    if (!name) {
      showToast(t.skills.nameRequired ?? "Skill name required", "error");
      return;
    }
    if (!/^[A-Za-z0-9][A-Za-z0-9_\-]{0,63}$/.test(name)) {
      showToast(t.skills.invalidName ?? "Invalid name", "error");
      return;
    }
    if (createCategory && !/^[A-Za-z0-9][A-Za-z0-9_\-/]{0,63}$/.test(createCategory.trim())) {
      showToast(t.skills.invalidCategory ?? "Invalid category", "error");
      return;
    }
    if (!createContent.trim()) {
      showToast(t.skills.contentRequired ?? "Content required", "error");
      return;
    }
    setCreating(true);
    try {
      await api.createSkill({
        name,
        category: createCategory.trim() || undefined,
        content: createContent,
      });
      showToast(t.skills.skillCreated ?? "Skill created", "success");
      setShowCreate(false);
      setCreateName("");
      setCreateCategory("");
      const list = await reloadSkills();
      const created = list.find((s) => s.name === name);
      if (created) {
        await openDetail(created);
      }
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : String(err);
      showToast(`${t.skills.createFailed ?? "Create failed"}: ${msg}`, "error");
    } finally {
      setCreating(false);
    }
  }, [createName, createCategory, createContent, reloadSkills, openDetail, showToast, t]);

  /* ---- Derived data ---- */
  const lowerSearch = search.toLowerCase();
  const isSearching = search.trim().length > 0;

  const searchMatchedSkills = useMemo(() => {
    if (!isSearching) return [];
    return skills.filter(
      (s) =>
        s.name.toLowerCase().includes(lowerSearch) ||
        s.description.toLowerCase().includes(lowerSearch) ||
        (s.category ?? "").toLowerCase().includes(lowerSearch),
    );
  }, [skills, isSearching, lowerSearch]);

  const activeSkills = useMemo(() => {
    if (isSearching) return [];
    if (!activeCategory)
      return [...skills].sort((a, b) => a.name.localeCompare(b.name));
    return skills
      .filter((s) =>
        activeCategory === "__none__"
          ? !s.category
          : s.category === activeCategory,
      )
      .sort((a, b) => a.name.localeCompare(b.name));
  }, [skills, activeCategory, isSearching]);

  const allCategories = useMemo(() => {
    const cats = new Map<string, number>();
    for (const s of skills) {
      const key = s.category || "__none__";
      cats.set(key, (cats.get(key) || 0) + 1);
    }
    return [...cats.entries()]
      .sort((a, b) => {
        if (a[0] === "__none__") return -1;
        if (b[0] === "__none__") return 1;
        return a[0].localeCompare(b[0]);
      })
      .map(([key, count]) => ({
        key,
        name: prettyCategory(key === "__none__" ? null : key, t.common.general),
        count,
      }));
  }, [skills, t]);

  const enabledCount = skills.filter((s) => s.enabled).length;

  useLayoutEffect(() => {
    if (loading) {
      setAfterTitle(null);
      setEnd(null);
      return;
    }
    if (selected) {
      setAfterTitle(
        <span className="whitespace-nowrap text-xs text-muted-foreground font-mono-ui">
          {selected.name}
        </span>,
      );
      setEnd(null);
      return () => {
        setAfterTitle(null);
        setEnd(null);
      };
    }
    setAfterTitle(
      <span className="whitespace-nowrap text-xs text-muted-foreground">
        {t.skills.enabledOf
          .replace("{enabled}", String(enabledCount))
          .replace("{total}", String(skills.length))}
      </span>,
    );
    setEnd(
      <div className="flex items-center gap-2 w-full sm:max-w-md">
        {view === "skills" && (
          <Button
            outlined
            size="xs"
            onClick={() => setShowCreate(true)}
            aria-label={t.skills.create ?? "New skill"}
            className="shrink-0"
          >
            <Plus />
            <span className="hidden sm:inline">
              {t.skills.create ?? "New skill"}
            </span>
          </Button>
        )}
        <div className="relative flex-1 min-w-0">
          <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-muted-foreground" />
          <Input
            className="h-8 pl-8 pr-7 text-xs"
            placeholder={t.common.search}
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
          {search && (
            <Button
              ghost
              size="xs"
              className="absolute right-1.5 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground"
              onClick={() => setSearch("")}
              aria-label={t.common.clear}
            >
              <X />
            </Button>
          )}
        </div>
      </div>,
    );
    return () => {
      setAfterTitle(null);
      setEnd(null);
    };
  }, [enabledCount, loading, search, selected, setAfterTitle, setEnd, skills.length, t, view]);

  const filteredToolsets = useMemo(() => {
    return toolsets.filter(
      (ts) =>
        !search ||
        ts.name.toLowerCase().includes(lowerSearch) ||
        ts.label.toLowerCase().includes(lowerSearch) ||
        ts.description.toLowerCase().includes(lowerSearch),
    );
  }, [toolsets, search, lowerSearch]);

  /* ---- Loading ---- */
  if (loading) {
    return (
      <div className="flex items-center justify-center py-24">
        <Spinner className="text-2xl text-primary" />
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-4">
      <PluginSlot name="skills:top" />
      <Toast toast={toast} />

      {selected ? (
        <SkillDetailPanel
          selected={selected}
          detail={detail}
          loading={detailLoading}
          editContent={editContent}
          setEditContent={setEditContent}
          saving={saving}
          onClose={closeDetail}
          onSave={handleSave}
          onDelete={() => setDeleteOpen(true)}
          onClone={handleCloneToUser}
          t={t}
        />
      ) : (
      <div className="flex flex-col sm:flex-row sm:items-start gap-4">
        <aside aria-label={t.skills.title} className="sm:w-56 sm:shrink-0">
          <div className="sm:sticky sm:top-0">
            <div
              className={`
                flex flex-col
                border border-border bg-muted/20
              `}
            >
              <div className="hidden sm:flex items-center gap-2 px-3 py-2 border-b border-border">
                <Filter className="h-3 w-3 text-muted-foreground" />
                <span className="font-mondwest text-[0.65rem] tracking-[0.12em] uppercase text-muted-foreground">
                  {t.skills.filters}
                </span>
              </div>

              <div className="flex sm:flex-col gap-1 overflow-x-auto sm:overflow-x-visible scrollbar-none p-2">
                <PanelItem
                  icon={Package}
                  label={`${t.skills.all} (${skills.length})`}
                  active={view === "skills" && !isSearching}
                  onClick={() => {
                    setView("skills");
                    setActiveCategory(null);
                    setSearch("");
                  }}
                />
                <PanelItem
                  icon={Wrench}
                  label={`${t.skills.toolsets} (${toolsets.length})`}
                  active={view === "toolsets"}
                  onClick={() => {
                    setView("toolsets");
                    setSearch("");
                  }}
                />
              </div>

              {view === "skills" &&
                !isSearching &&
                allCategories.length > 0 && (
                  <div className="hidden sm:flex flex-col border-t border-border">
                    <div className="px-3 pt-2 pb-1 font-mondwest text-[0.6rem] tracking-[0.12em] uppercase text-muted-foreground/70">
                      {t.skills.categories}
                    </div>
                    <div className="flex flex-col p-2 pt-1 gap-px max-h-[calc(100vh-340px)] overflow-y-auto">
                      {allCategories.map(({ key, name, count }) => {
                        const isActive = activeCategory === key;

                        return (
                          <ListItem
                            key={key}
                            active={isActive}
                            onClick={() =>
                              setActiveCategory(isActive ? null : key)
                            }
                            className="rounded-sm px-2 py-1 text-[11px]"
                          >
                            <span className="flex-1 truncate">{name}</span>
                            <span
                              className={`text-[10px] tabular-nums ${
                                isActive
                                  ? "text-foreground/60"
                                  : "text-muted-foreground/50"
                              }`}
                            >
                              {count}
                            </span>
                          </ListItem>
                        );
                      })}
                    </div>
                  </div>
                )}
            </div>
          </div>
        </aside>

        <div className="flex-1 min-w-0">
          {isSearching ? (
            <Card>
              <CardHeader className="py-3 px-4">
                <div className="flex items-center justify-between">
                  <CardTitle className="text-sm flex items-center gap-2">
                    <Search className="h-4 w-4" />
                    {t.skills.title}
                  </CardTitle>
                  <Badge tone="secondary" className="text-[10px]">
                    {t.skills.resultCount
                      .replace("{count}", String(searchMatchedSkills.length))
                      .replace(
                        "{s}",
                        searchMatchedSkills.length !== 1 ? "s" : "",
                      )}
                  </Badge>
                </div>
              </CardHeader>
              <CardContent className="px-4 pb-4">
                {searchMatchedSkills.length === 0 ? (
                  <p className="text-sm text-muted-foreground text-center py-8">
                    {t.skills.noSkillsMatch}
                  </p>
                ) : (
                  <div className="grid gap-1">
                    {searchMatchedSkills.map((skill) => (
                      <SkillRow
                        key={skill.name}
                        skill={skill}
                        toggling={togglingSkills.has(skill.name)}
                        onToggle={() => handleToggleSkill(skill)}
                        onSelect={() => openDetail(skill)}
                        noDescriptionLabel={t.skills.noDescription}
                        readOnlyLabel={t.skills.readOnlyBadge ?? "Read-only"}
                      />
                    ))}
                  </div>
                )}
              </CardContent>
            </Card>
          ) : view === "skills" ? (
            /* Skills list */
            <Card>
              <CardHeader className="py-3 px-4">
                <div className="flex items-center justify-between">
                  <CardTitle className="text-sm flex items-center gap-2">
                    <Package className="h-4 w-4" />
                    {activeCategory
                      ? prettyCategory(
                          activeCategory === "__none__" ? null : activeCategory,
                          t.common.general,
                        )
                      : t.skills.all}
                  </CardTitle>
                  <Badge tone="secondary" className="text-[10px]">
                    {t.skills.skillCount
                      .replace("{count}", String(activeSkills.length))
                      .replace("{s}", activeSkills.length !== 1 ? "s" : "")}
                  </Badge>
                </div>
              </CardHeader>
              <CardContent className="px-4 pb-4">
                {activeSkills.length === 0 ? (
                  <p className="text-sm text-muted-foreground text-center py-8">
                    {skills.length === 0
                      ? t.skills.noSkills
                      : t.skills.noSkillsMatch}
                  </p>
                ) : (
                  <div className="grid gap-1">
                    {activeSkills.map((skill) => (
                      <SkillRow
                        key={skill.name}
                        skill={skill}
                        toggling={togglingSkills.has(skill.name)}
                        onToggle={() => handleToggleSkill(skill)}
                        onSelect={() => openDetail(skill)}
                        noDescriptionLabel={t.skills.noDescription}
                        readOnlyLabel={t.skills.readOnlyBadge ?? "Read-only"}
                      />
                    ))}
                  </div>
                )}
              </CardContent>
            </Card>
          ) : (
            /* Toolsets grid */
            <>
              {filteredToolsets.length === 0 ? (
                <Card>
                  <CardContent className="py-8 text-center text-sm text-muted-foreground">
                    {t.skills.noToolsetsMatch}
                  </CardContent>
                </Card>
              ) : (
                <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
                  {filteredToolsets.map((ts) => {
                    const TsIcon = toolsetIcon(ts.name);
                    const labelText =
                      ts.label.replace(/^[\p{Emoji}\s]+/u, "").trim() ||
                      ts.name;

                    return (
                      <Card key={ts.name} className="relative">
                        <CardContent className="py-4">
                          <div className="flex items-start gap-3">
                            <TsIcon className="h-5 w-5 text-muted-foreground shrink-0 mt-0.5" />
                            <div className="flex-1 min-w-0">
                              <div className="flex items-center gap-2 mb-1">
                                <span className="font-medium text-sm">
                                  {labelText}
                                </span>
                                <Badge
                                  tone={ts.enabled ? "success" : "outline"}
                                  className="text-[10px]"
                                >
                                  {ts.enabled
                                    ? t.common.active
                                    : t.common.inactive}
                                </Badge>
                              </div>
                              <p className="text-xs text-muted-foreground mb-2">
                                {ts.description}
                              </p>
                              {ts.enabled && !ts.configured && (
                                <p className="text-[10px] text-amber-300/80 mb-2">
                                  {t.skills.setupNeeded}
                                </p>
                              )}
                              {ts.tools.length > 0 && (
                                <div className="flex flex-wrap gap-1">
                                  {ts.tools.map((tool) => (
                                    <Badge
                                      key={tool}
                                      tone="secondary"
                                      className="text-[10px] font-mono"
                                    >
                                      {tool}
                                    </Badge>
                                  ))}
                                </div>
                              )}
                              {ts.tools.length === 0 && (
                                <span className="text-[10px] text-muted-foreground/60">
                                  {ts.enabled
                                    ? t.skills.toolsetLabel.replace(
                                        "{name}",
                                        ts.name,
                                      )
                                    : t.skills.disabledForCli}
                                </span>
                              )}
                            </div>
                          </div>
                        </CardContent>
                      </Card>
                    );
                  })}
                </div>
              )}
            </>
          )}
        </div>
      </div>
      )}
      <PluginSlot name="skills:bottom" />

      <ConfirmDialog
        open={deleteOpen}
        title={t.skills.deleteConfirmTitle ?? "Delete skill"}
        description={
          (t.skills.deleteConfirmHint ?? "This will permanently delete the skill.") +
          (detail ? `\n${detail.name}` : "")
        }
        confirmLabel={t.skills.delete ?? "Delete"}
        cancelLabel={t.skills.cancel ?? "Cancel"}
        destructive
        loading={deleting}
        onCancel={() => !deleting && setDeleteOpen(false)}
        onConfirm={handleDelete}
      />

      {showCreate && (
        <div
          role="dialog"
          aria-modal="true"
          aria-labelledby="create-skill-title"
          onClick={(e) => {
            if (e.target === e.currentTarget && !creating) setShowCreate(false);
          }}
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm"
        >
          <div className="relative w-full max-w-2xl mx-4 border border-border bg-card shadow-lg flex flex-col">
            <div className="flex items-center justify-between p-4 border-b border-border">
              <h2
                id="create-skill-title"
                className="font-expanded text-sm font-bold tracking-[0.08em] uppercase"
              >
                {t.skills.createTitle ?? "Create skill"}
              </h2>
              <Button
                ghost
                size="xs"
                onClick={() => !creating && setShowCreate(false)}
                aria-label={t.skills.cancel ?? "Cancel"}
              >
                <X />
              </Button>
            </div>
            <div className="flex flex-col gap-3 p-4">
              <Input
                placeholder={t.skills.namePlaceholder ?? "skill-name"}
                value={createName}
                onChange={(e) => setCreateName(e.target.value)}
                disabled={creating}
              />
              <Input
                placeholder={
                  t.skills.categoryPlaceholder ?? "category (optional)"
                }
                value={createCategory}
                onChange={(e) => setCreateCategory(e.target.value)}
                disabled={creating}
              />
              <textarea
                value={createContent}
                onChange={(e) => setCreateContent(e.target.value)}
                disabled={creating}
                spellCheck={false}
                className="font-mono text-xs min-h-[280px] w-full p-3 border border-border bg-muted/10 outline-none focus:border-primary"
              />
            </div>
            <div className="flex items-center justify-end gap-2 p-3 border-t border-border">
              <Button
                outlined
                onClick={() => setShowCreate(false)}
                disabled={creating}
              >
                {t.skills.cancel ?? "Cancel"}
              </Button>
              <Button onClick={handleCreate} disabled={creating}>
                {creating ? "…" : t.skills.create ?? "Create"}
              </Button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

function SkillRow({
  skill,
  toggling,
  onToggle,
  onSelect,
  noDescriptionLabel,
  readOnlyLabel,
}: SkillRowProps) {
  return (
    <div
      role="button"
      tabIndex={0}
      onClick={onSelect}
      onKeyDown={(e) => {
        if (e.key === "Enter" || e.key === " ") {
          e.preventDefault();
          onSelect();
        }
      }}
      className="group flex items-start gap-3 px-3 py-2.5 transition-colors hover:bg-muted/40 cursor-pointer focus:outline-none focus:bg-muted/40"
    >
      <div
        className="pt-0.5 shrink-0"
        onClick={(e) => e.stopPropagation()}
        onKeyDown={(e) => e.stopPropagation()}
      >
        <Switch
          checked={skill.enabled}
          onCheckedChange={onToggle}
          disabled={toggling}
        />
      </div>
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2 mb-0.5">
          <span
            className={`font-mono-ui text-sm ${
              skill.enabled ? "text-foreground" : "text-muted-foreground"
            }`}
          >
            {skill.name}
          </span>
          {skill.writable === false && (
            <span
              className="inline-flex items-center gap-0.5 text-[9px] uppercase tracking-wider text-muted-foreground/70"
              title={readOnlyLabel}
            >
              <Lock className="h-2.5 w-2.5" />
              {readOnlyLabel}
            </span>
          )}
        </div>
        <p className="text-xs text-muted-foreground leading-relaxed line-clamp-2">
          {skill.description || noDescriptionLabel}
        </p>
      </div>
    </div>
  );
}

function SkillDetailPanel({
  selected,
  detail,
  loading,
  editContent,
  setEditContent,
  saving,
  onClose,
  onSave,
  onDelete,
  onClone,
  t,
}: SkillDetailPanelProps) {
  return (
    <Card>
      <CardHeader className="py-3 px-4">
        <div className="flex items-center justify-between flex-wrap gap-2">
          <CardTitle className="text-sm flex items-center gap-2 min-w-0">
            <Button
              ghost
              size="xs"
              onClick={onClose}
              aria-label={t.skills.backToList ?? "Back"}
            >
              <ArrowLeft />
            </Button>
            <Package className="h-4 w-4 shrink-0" />
            <span className="font-mono-ui truncate">{selected.name}</span>
            {detail?.category && (
              <Badge tone="secondary" className="text-[10px]">
                {prettyCategory(detail.category, t.common.general)}
              </Badge>
            )}
            {detail && !detail.writable && (
              <Badge
                tone="outline"
                className="text-[10px] inline-flex items-center gap-1"
              >
                <Lock className="h-2.5 w-2.5" />
                {t.skills.readOnlyBadge ?? "Read-only"}
              </Badge>
            )}
          </CardTitle>
          <div className="flex items-center gap-2">
            {detail?.writable && (
              <>
                <Button onClick={onSave} disabled={saving} size="sm">
                  <Save />
                  {saving
                    ? t.skills.saving ?? "Saving..."
                    : t.skills.save ?? "Save"}
                </Button>
                <Button
                  outlined
                  destructive
                  onClick={onDelete}
                  disabled={saving}
                  size="sm"
                >
                  <Trash2 />
                  {t.skills.delete ?? "Delete"}
                </Button>
              </>
            )}
            {detail && !detail.writable && (
              <Button onClick={onClone} disabled={saving} size="sm">
                <Copy />
                {t.skills.cloneToUser ?? "Clone to user dir"}
              </Button>
            )}
          </div>
        </div>
      </CardHeader>
      <CardContent className="px-4 pb-4 flex flex-col gap-3">
        {loading ? (
          <div className="py-12 flex items-center justify-center">
            <Spinner className="text-2xl text-primary" />
          </div>
        ) : detail ? (
          <>
            <div className="grid gap-1 text-xs text-muted-foreground">
              {detail.description && <div>{detail.description}</div>}
              {detail.source_dir && (
                <div>
                  <span className="uppercase text-[9px] tracking-wider mr-1">
                    {t.skills.sourceDir ?? "Source"}:
                  </span>
                  <span className="font-mono">{detail.source_dir}</span>
                </div>
              )}
              {detail.path && (
                <div>
                  <span className="uppercase text-[9px] tracking-wider mr-1">
                    {t.skills.pathLabel ?? "Path"}:
                  </span>
                  <span className="font-mono break-all">{detail.path}</span>
                </div>
              )}
              {!detail.writable && (
                <div className="text-amber-300/80 text-[11px]">
                  {t.skills.readOnlyHint ??
                    "Built-in skill is read-only. Clone to ~/.hermes/skills/ to edit."}
                </div>
              )}
            </div>
            <textarea
              value={editContent}
              onChange={(e) => setEditContent(e.target.value)}
              disabled={!detail.writable || saving}
              spellCheck={false}
              className="font-mono text-xs min-h-[420px] w-full p-3 border border-border bg-muted/10 outline-none focus:border-primary disabled:opacity-70"
            />
          </>
        ) : (
          <p className="text-sm text-muted-foreground text-center py-8">
            {t.skills.loadDetailFailed ?? "Failed to load"}
          </p>
        )}
      </CardContent>
    </Card>
  );
}

function PanelItem({ active, icon: Icon, label, onClick }: PanelItemProps) {
  return (
    <ListItem
      active={active}
      onClick={onClick}
      className={cn(
        "rounded-sm whitespace-nowrap px-2.5 py-1.5",
        "font-mondwest text-[0.7rem] tracking-[0.08em] uppercase",
        active && "bg-foreground/90 text-background hover:text-background",
      )}
    >
      <Icon className="h-3.5 w-3.5 shrink-0" />
      <span className="flex-1 truncate">{label}</span>
    </ListItem>
  );
}

interface PanelItemProps {
  active: boolean;
  icon: React.ComponentType<{ className?: string }>;
  label: string;
  onClick: () => void;
}

interface SkillRowProps {
  noDescriptionLabel: string;
  readOnlyLabel: string;
  onSelect: () => void;
  onToggle: () => void;
  skill: SkillInfo;
  toggling: boolean;
}

interface SkillDetailPanelProps {
  selected: SkillInfo;
  detail: SkillDetail | null;
  loading: boolean;
  editContent: string;
  setEditContent: (v: string) => void;
  saving: boolean;
  onClose: () => void;
  onSave: () => void;
  onDelete: () => void;
  onClone: () => void;
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  t: any;
}
