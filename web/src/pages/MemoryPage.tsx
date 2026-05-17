import { useCallback, useEffect, useLayoutEffect, useMemo, useState } from "react";
import {
  Database,
  Search,
  X,
  Plus,
  Save,
  Trash2,
  RefreshCcw,
  ArrowLeft,
  Tag,
  TrendingUp,
  TrendingDown,
} from "lucide-react";
import { api } from "@/lib/api";
import type {
  MemoryFact,
  MemoryFactDetail,
  MemoryEntity,
  MemoryBank,
  MemoryStats,
} from "@/lib/api";
import { useToast } from "@/hooks/useToast";
import { Toast } from "@/components/Toast";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { ConfirmDialog } from "@/components/ui/confirm-dialog";
import { Badge } from "@nous-research/ui/ui/components/badge";
import { Button } from "@nous-research/ui/ui/components/button";
import { ListItem } from "@nous-research/ui/ui/components/list-item";
import { Spinner } from "@nous-research/ui/ui/components/spinner";
import { Input } from "@/components/ui/input";
import { useI18n } from "@/i18n";
import { usePageHeader } from "@/contexts/usePageHeader";

type Tab = "facts" | "entities" | "banks";

function formatTime(value: string | null | undefined): string {
  if (!value) return "—";
  const d = new Date(value);
  if (Number.isNaN(d.getTime())) return value;
  return d.toLocaleString();
}

export default function MemoryPage() {
  const [tab, setTab] = useState<Tab>("facts");
  const [stats, setStats] = useState<MemoryStats | null>(null);
  const [loading, setLoading] = useState(true);

  // facts state
  const [facts, setFacts] = useState<MemoryFact[]>([]);
  const [factsLoading, setFactsLoading] = useState(false);
  const [search, setSearch] = useState("");
  const [minTrust, setMinTrust] = useState<number>(0);
  const [activeCategory, setActiveCategory] = useState<string | null>(null);
  const [selectedFact, setSelectedFact] = useState<MemoryFactDetail | null>(null);
  const [factDetailLoading, setFactDetailLoading] = useState(false);
  const [editContent, setEditContent] = useState("");
  const [editCategory, setEditCategory] = useState("");
  const [editTags, setEditTags] = useState("");
  const [saving, setSaving] = useState(false);
  const [deleteOpen, setDeleteOpen] = useState(false);
  const [deleting, setDeleting] = useState(false);

  // create fact
  const [showCreate, setShowCreate] = useState(false);
  const [createContent, setCreateContent] = useState("");
  const [createCategory, setCreateCategory] = useState("");
  const [createTags, setCreateTags] = useState("");
  const [creating, setCreating] = useState(false);

  // entities
  const [entities, setEntities] = useState<MemoryEntity[]>([]);
  const [entitiesLoading, setEntitiesLoading] = useState(false);

  // banks
  const [banks, setBanks] = useState<MemoryBank[]>([]);
  const [banksLoading, setBanksLoading] = useState(false);
  const [rebuilding, setRebuilding] = useState<string | null>(null);

  const { toast, showToast } = useToast();
  const { t } = useI18n();
  const { setAfterTitle, setEnd } = usePageHeader();

  const reloadStats = useCallback(async () => {
    try {
      const s = await api.getMemoryStats();
      setStats(s);
    } catch {
      /* noop */
    }
  }, []);

  const loadFacts = useCallback(async () => {
    setFactsLoading(true);
    try {
      const params: { q?: string; category?: string; min_trust?: number; limit?: number } = {
        limit: 500,
      };
      if (search.trim()) params.q = search.trim();
      if (activeCategory) params.category = activeCategory;
      if (minTrust > 0) params.min_trust = minTrust;
      const res = await api.listMemoryFacts(params);
      setFacts(res.facts);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : String(err);
      showToast(`${t.memory?.loadFailed ?? "Load failed"}: ${msg}`, "error");
    } finally {
      setFactsLoading(false);
    }
  }, [search, activeCategory, minTrust, showToast, t]);

  const loadEntities = useCallback(async () => {
    setEntitiesLoading(true);
    try {
      const res = await api.listMemoryEntities(500);
      setEntities(res.entities);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : String(err);
      showToast(`${t.memory?.loadFailed ?? "Load failed"}: ${msg}`, "error");
    } finally {
      setEntitiesLoading(false);
    }
  }, [showToast, t]);

  const loadBanks = useCallback(async () => {
    setBanksLoading(true);
    try {
      const res = await api.listMemoryBanks();
      setBanks(res.banks);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : String(err);
      showToast(`${t.memory?.loadFailed ?? "Load failed"}: ${msg}`, "error");
    } finally {
      setBanksLoading(false);
    }
  }, [showToast, t]);

  useEffect(() => {
    Promise.all([reloadStats(), loadFacts()]).finally(() => setLoading(false));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Reload facts when filters change
  useEffect(() => {
    if (loading) return;
    if (tab !== "facts") return;
    const id = setTimeout(() => {
      loadFacts();
    }, 250);
    return () => clearTimeout(id);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [search, activeCategory, minTrust, tab]);

  useEffect(() => {
    if (tab === "entities" && entities.length === 0 && !entitiesLoading) loadEntities();
    if (tab === "banks" && banks.length === 0 && !banksLoading) loadBanks();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [tab]);

  const openFact = useCallback(
    async (fact: MemoryFact) => {
      setFactDetailLoading(true);
      try {
        const d = await api.getMemoryFact(fact.fact_id);
        setSelectedFact(d);
        setEditContent(d.content);
        setEditCategory(d.category);
        setEditTags(d.tags);
      } catch (err: unknown) {
        const msg = err instanceof Error ? err.message : String(err);
        showToast(`${t.memory?.loadFailed ?? "Load failed"}: ${msg}`, "error");
      } finally {
        setFactDetailLoading(false);
      }
    },
    [showToast, t],
  );

  const closeFact = useCallback(() => {
    setSelectedFact(null);
    setEditContent("");
    setEditCategory("");
    setEditTags("");
  }, []);

  const handleSaveFact = useCallback(async () => {
    if (!selectedFact) return;
    if (!editContent.trim()) {
      showToast(t.memory?.contentRequired ?? "Content required", "error");
      return;
    }
    setSaving(true);
    try {
      await api.updateMemoryFact(selectedFact.fact_id, {
        content: editContent,
        category: editCategory,
        tags: editTags,
      });
      showToast(t.memory?.saved ?? "Saved", "success");
      const fresh = await api.getMemoryFact(selectedFact.fact_id);
      setSelectedFact(fresh);
      await Promise.all([loadFacts(), reloadStats()]);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : String(err);
      showToast(`${t.memory?.saveFailed ?? "Save failed"}: ${msg}`, "error");
    } finally {
      setSaving(false);
    }
  }, [selectedFact, editContent, editCategory, editTags, loadFacts, reloadStats, showToast, t]);

  const handleTrustDelta = useCallback(
    async (delta: number) => {
      if (!selectedFact) return;
      setSaving(true);
      try {
        await api.updateMemoryFact(selectedFact.fact_id, { trust_delta: delta });
        const fresh = await api.getMemoryFact(selectedFact.fact_id);
        setSelectedFact(fresh);
        await loadFacts();
      } catch (err: unknown) {
        const msg = err instanceof Error ? err.message : String(err);
        showToast(`${t.memory?.saveFailed ?? "Save failed"}: ${msg}`, "error");
      } finally {
        setSaving(false);
      }
    },
    [selectedFact, loadFacts, showToast, t],
  );

  const handleDeleteFact = useCallback(async () => {
    if (!selectedFact) return;
    setDeleting(true);
    try {
      await api.deleteMemoryFact(selectedFact.fact_id);
      showToast(t.memory?.deleted ?? "Deleted", "success");
      setDeleteOpen(false);
      closeFact();
      await Promise.all([loadFacts(), reloadStats()]);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : String(err);
      showToast(`${t.memory?.deleteFailed ?? "Delete failed"}: ${msg}`, "error");
    } finally {
      setDeleting(false);
    }
  }, [selectedFact, closeFact, loadFacts, reloadStats, showToast, t]);

  const handleCreateFact = useCallback(async () => {
    if (!createContent.trim()) {
      showToast(t.memory?.contentRequired ?? "Content required", "error");
      return;
    }
    setCreating(true);
    try {
      await api.createMemoryFact({
        content: createContent,
        category: createCategory.trim() || undefined,
        tags: createTags.trim() || undefined,
      });
      showToast(t.memory?.factCreated ?? "Created", "success");
      setShowCreate(false);
      setCreateContent("");
      setCreateCategory("");
      setCreateTags("");
      await Promise.all([loadFacts(), reloadStats()]);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : String(err);
      showToast(`${t.memory?.factCreateFailed ?? "Create failed"}: ${msg}`, "error");
    } finally {
      setCreating(false);
    }
  }, [createContent, createCategory, createTags, loadFacts, reloadStats, showToast, t]);

  const handleRebuildBank = useCallback(
    async (category: string) => {
      setRebuilding(category);
      try {
        await api.rebuildMemoryBank(category);
        showToast(t.memory?.rebuildSuccess ?? "Rebuilt", "success");
        await Promise.all([loadBanks(), reloadStats()]);
      } catch (err: unknown) {
        const msg = err instanceof Error ? err.message : String(err);
        showToast(`${t.memory?.rebuildFailed ?? "Rebuild failed"}: ${msg}`, "error");
      } finally {
        setRebuilding(null);
      }
    },
    [loadBanks, reloadStats, showToast, t],
  );

  const categories = useMemo(() => stats?.categories ?? [], [stats]);

  useLayoutEffect(() => {
    if (loading) {
      setAfterTitle(null);
      setEnd(null);
      return;
    }
    setAfterTitle(
      stats ? (
        <span className="whitespace-nowrap text-xs text-muted-foreground">
          {(t.memory?.factCount ?? "{count} facts").replace("{count}", String(stats.facts))}
          {" · "}
          {stats.backend}
        </span>
      ) : null,
    );
    setEnd(
      tab === "facts" ? (
        <div className="flex items-center gap-2 w-full sm:max-w-md">
          <Button
            outlined
            size="xs"
            onClick={() => setShowCreate(true)}
            aria-label={t.memory?.addFact ?? "Add fact"}
            className="shrink-0"
          >
            <Plus />
            <span className="hidden sm:inline">{t.memory?.addFact ?? "Add fact"}</span>
          </Button>
          <div className="relative flex-1 min-w-0">
            <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-muted-foreground" />
            <Input
              className="h-8 pl-8 pr-7 text-xs"
              placeholder={t.memory?.searchPlaceholder ?? "Search facts..."}
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
        </div>
      ) : null,
    );
    return () => {
      setAfterTitle(null);
      setEnd(null);
    };
  }, [loading, search, stats, tab, setAfterTitle, setEnd, t]);

  if (loading) {
    return (
      <div className="flex items-center justify-center py-24">
        <Spinner className="text-2xl text-primary" />
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-4">
      <Toast toast={toast} />

      {/* Tab bar */}
      <div className="flex items-center gap-1 border border-border bg-muted/20 p-1 self-start">
        {(["facts", "entities", "banks"] as Tab[]).map((key) => (
          <button
            key={key}
            type="button"
            onClick={() => {
              setTab(key);
              if (key === "facts") closeFact();
            }}
            className={`px-3 py-1.5 text-[11px] font-mondwest uppercase tracking-[0.12em] ${
              tab === key
                ? "bg-foreground/90 text-background"
                : "text-muted-foreground hover:text-foreground"
            }`}
          >
            {key === "facts"
              ? t.memory?.factsTab ?? "Facts"
              : key === "entities"
                ? t.memory?.entitiesTab ?? "Entities"
                : t.memory?.banksTab ?? "Banks"}
          </button>
        ))}
      </div>

      {tab === "facts" ? (
        selectedFact ? (
          <FactDetailPanel
            fact={selectedFact}
            loading={factDetailLoading}
            editContent={editContent}
            editCategory={editCategory}
            editTags={editTags}
            saving={saving}
            setEditContent={setEditContent}
            setEditCategory={setEditCategory}
            setEditTags={setEditTags}
            onClose={closeFact}
            onSave={handleSaveFact}
            onDelete={() => setDeleteOpen(true)}
            onTrustDelta={handleTrustDelta}
            t={t}
          />
        ) : (
          <div className="flex flex-col sm:flex-row sm:items-start gap-4">
            <aside className="sm:w-56 sm:shrink-0">
              <div className="flex flex-col border border-border bg-muted/20">
                <div className="px-3 py-2 border-b border-border font-mondwest text-[0.65rem] tracking-[0.12em] uppercase text-muted-foreground">
                  {t.memory?.factsByCategory ?? "Categories"}
                </div>
                <div className="flex flex-col p-2 gap-px max-h-[60vh] overflow-y-auto">
                  <ListItem
                    active={activeCategory === null}
                    onClick={() => setActiveCategory(null)}
                    className="rounded-sm px-2 py-1 text-[11px]"
                  >
                    <span className="flex-1 truncate">{t.skills.all ?? "All"}</span>
                    <span className="text-[10px] tabular-nums text-muted-foreground/70">
                      {stats?.facts ?? 0}
                    </span>
                  </ListItem>
                  {categories.map(({ category, count }) => {
                    const active = activeCategory === category;
                    return (
                      <ListItem
                        key={category || "__none__"}
                        active={active}
                        onClick={() =>
                          setActiveCategory(active ? null : category || "")
                        }
                        className="rounded-sm px-2 py-1 text-[11px]"
                      >
                        <span className="flex-1 truncate">{category || "(none)"}</span>
                        <span className="text-[10px] tabular-nums text-muted-foreground/70">
                          {count}
                        </span>
                      </ListItem>
                    );
                  })}
                </div>
                <div className="px-3 py-2 border-t border-border flex items-center gap-2">
                  <span className="text-[10px] uppercase tracking-wider text-muted-foreground/70">
                    {t.memory?.minTrustLabel ?? "Min trust"}
                  </span>
                  <Input
                    className="h-7 w-16 text-xs"
                    type="number"
                    step={0.1}
                    min={0}
                    max={1}
                    value={minTrust}
                    onChange={(e) => setMinTrust(parseFloat(e.target.value) || 0)}
                  />
                </div>
              </div>
            </aside>

            <div className="flex-1 min-w-0">
              <Card>
                <CardHeader className="py-3 px-4">
                  <div className="flex items-center justify-between">
                    <CardTitle className="text-sm flex items-center gap-2">
                      <Database className="h-4 w-4" />
                      {t.memory?.factsTab ?? "Facts"}
                    </CardTitle>
                    <Badge tone="secondary" className="text-[10px]">
                      {(t.memory?.factCount ?? "{count} facts").replace(
                        "{count}",
                        String(facts.length),
                      )}
                    </Badge>
                  </div>
                </CardHeader>
                <CardContent className="px-4 pb-4">
                  {factsLoading ? (
                    <div className="py-12 flex items-center justify-center">
                      <Spinner className="text-xl text-primary" />
                    </div>
                  ) : facts.length === 0 ? (
                    <p className="text-sm text-muted-foreground text-center py-8">
                      {t.memory?.noFacts ?? "No facts yet."}
                    </p>
                  ) : (
                    <div className="grid gap-1">
                      {facts.map((f) => (
                        <FactRow key={f.fact_id} fact={f} onSelect={() => openFact(f)} />
                      ))}
                    </div>
                  )}
                </CardContent>
              </Card>
            </div>
          </div>
        )
      ) : tab === "entities" ? (
        <Card>
          <CardHeader className="py-3 px-4">
            <div className="flex items-center justify-between">
              <CardTitle className="text-sm flex items-center gap-2">
                <Tag className="h-4 w-4" />
                {t.memory?.entitiesTab ?? "Entities"}
              </CardTitle>
              <Badge tone="secondary" className="text-[10px]">
                {(t.memory?.entityCount ?? "{count} entities").replace(
                  "{count}",
                  String(entities.length),
                )}
              </Badge>
            </div>
            <p className="text-[11px] text-muted-foreground mt-1">
              {t.memory?.factDimDerived ??
                "Entities & banks are derived from facts and read-only."}
            </p>
          </CardHeader>
          <CardContent className="px-4 pb-4">
            {entitiesLoading ? (
              <div className="py-12 flex items-center justify-center">
                <Spinner className="text-xl text-primary" />
              </div>
            ) : entities.length === 0 ? (
              <p className="text-sm text-muted-foreground text-center py-8">
                {t.memory?.noEntities ?? "No entities."}
              </p>
            ) : (
              <div className="grid gap-1">
                {entities.map((e) => (
                  <div
                    key={e.entity_id}
                    className="flex items-start gap-3 px-3 py-2 border-b border-border/40 last:border-b-0"
                  >
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 mb-0.5">
                        <span className="font-mono-ui text-sm">{e.name}</span>
                        {e.entity_type && (
                          <Badge tone="outline" className="text-[10px]">
                            {e.entity_type}
                          </Badge>
                        )}
                      </div>
                      {e.aliases && (
                        <p className="text-[11px] text-muted-foreground">
                          {e.aliases}
                        </p>
                      )}
                    </div>
                    <Badge tone="secondary" className="text-[10px] shrink-0">
                      {e.fact_count} {(t.memory?.factsTab ?? "facts").toLowerCase()}
                    </Badge>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>
      ) : (
        <Card>
          <CardHeader className="py-3 px-4">
            <div className="flex items-center justify-between">
              <CardTitle className="text-sm flex items-center gap-2">
                <Database className="h-4 w-4" />
                {t.memory?.banksTab ?? "Banks"}
              </CardTitle>
              <Badge tone="secondary" className="text-[10px]">
                {(t.memory?.bankCount ?? "{count} banks").replace(
                  "{count}",
                  String(banks.length),
                )}
              </Badge>
            </div>
            <p className="text-[11px] text-muted-foreground mt-1">
              {t.memory?.factDimDerived ??
                "Banks are auto-built from facts grouped by category."}
            </p>
          </CardHeader>
          <CardContent className="px-4 pb-4">
            {banksLoading ? (
              <div className="py-12 flex items-center justify-center">
                <Spinner className="text-xl text-primary" />
              </div>
            ) : banks.length === 0 ? (
              <p className="text-sm text-muted-foreground text-center py-8">
                {t.memory?.noBanks ?? "No banks."}
              </p>
            ) : (
              <div className="grid gap-1">
                {banks.map((b) => (
                  <div
                    key={b.bank_name}
                    className="flex items-center gap-3 px-3 py-2 border-b border-border/40 last:border-b-0"
                  >
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 mb-0.5">
                        <span className="font-mono-ui text-sm">{b.bank_name}</span>
                        {b.category && (
                          <Badge tone="outline" className="text-[10px]">
                            {b.category}
                          </Badge>
                        )}
                      </div>
                      <p className="text-[11px] text-muted-foreground">
                        {b.fact_count} facts · dim {b.dim} · {formatTime(b.updated_at)}
                      </p>
                    </div>
                    <Button
                      outlined
                      size="xs"
                      onClick={() => handleRebuildBank(b.category)}
                      disabled={rebuilding === b.category}
                    >
                      <RefreshCcw />
                      {rebuilding === b.category
                        ? t.memory?.rebuilding ?? "Rebuilding..."
                        : t.memory?.rebuild ?? "Rebuild"}
                    </Button>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>
      )}

      <ConfirmDialog
        open={deleteOpen}
        title={t.memory?.deleteConfirm ?? "Delete fact"}
        description={
          (t.memory?.deleteConfirmHint ?? "This will permanently remove the fact.") +
          (selectedFact ? `\n#${selectedFact.fact_id}` : "")
        }
        confirmLabel={t.memory?.delete ?? "Delete"}
        cancelLabel={t.memory?.cancel ?? "Cancel"}
        destructive
        loading={deleting}
        onCancel={() => !deleting && setDeleteOpen(false)}
        onConfirm={handleDeleteFact}
      />

      {showCreate && (
        <div
          role="dialog"
          aria-modal="true"
          aria-labelledby="create-fact-title"
          onClick={(e) => {
            if (e.target === e.currentTarget && !creating) setShowCreate(false);
          }}
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm"
        >
          <div className="relative w-full max-w-xl mx-4 border border-border bg-card shadow-lg flex flex-col">
            <div className="flex items-center justify-between p-4 border-b border-border">
              <h2
                id="create-fact-title"
                className="font-expanded text-sm font-bold tracking-[0.08em] uppercase"
              >
                {t.memory?.addFactTitle ?? "Add fact"}
              </h2>
              <Button
                ghost
                size="xs"
                onClick={() => !creating && setShowCreate(false)}
                aria-label={t.memory?.cancel ?? "Cancel"}
              >
                <X />
              </Button>
            </div>
            <div className="flex flex-col gap-3 p-4">
              <textarea
                value={createContent}
                onChange={(e) => setCreateContent(e.target.value)}
                disabled={creating}
                placeholder={t.memory?.contentLabel ?? "Content"}
                spellCheck={false}
                className="font-mono text-xs min-h-[160px] w-full p-3 border border-border bg-muted/10 outline-none focus:border-primary"
              />
              <Input
                placeholder={t.memory?.categoryLabel ?? "Category (optional)"}
                value={createCategory}
                onChange={(e) => setCreateCategory(e.target.value)}
                disabled={creating}
              />
              <Input
                placeholder={t.memory?.tagsLabel ?? "Tags (comma separated)"}
                value={createTags}
                onChange={(e) => setCreateTags(e.target.value)}
                disabled={creating}
              />
            </div>
            <div className="flex items-center justify-end gap-2 p-3 border-t border-border">
              <Button outlined onClick={() => setShowCreate(false)} disabled={creating}>
                {t.memory?.cancel ?? "Cancel"}
              </Button>
              <Button onClick={handleCreateFact} disabled={creating}>
                {creating ? "…" : t.memory?.addFact ?? "Add"}
              </Button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

function FactRow({ fact, onSelect }: { fact: MemoryFact; onSelect: () => void }) {
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
      className="flex items-start gap-3 px-3 py-2.5 transition-colors hover:bg-muted/40 cursor-pointer focus:outline-none focus:bg-muted/40 border-b border-border/40 last:border-b-0"
    >
      <div className="flex-1 min-w-0">
        <p className="text-sm leading-relaxed line-clamp-2">{fact.content}</p>
        <div className="flex items-center gap-2 mt-1 flex-wrap">
          {fact.category && (
            <Badge tone="outline" className="text-[10px]">
              {fact.category}
            </Badge>
          )}
          {fact.tags && (
            <span className="text-[10px] text-muted-foreground/80 font-mono">{fact.tags}</span>
          )}
          <span className="text-[10px] text-muted-foreground/70 tabular-nums">
            trust {fact.trust_score?.toFixed?.(2) ?? fact.trust_score}
          </span>
          <span className="text-[10px] text-muted-foreground/70 tabular-nums">
            #{fact.fact_id}
          </span>
        </div>
      </div>
    </div>
  );
}

interface FactDetailPanelProps {
  fact: MemoryFactDetail;
  loading: boolean;
  editContent: string;
  editCategory: string;
  editTags: string;
  saving: boolean;
  setEditContent: (v: string) => void;
  setEditCategory: (v: string) => void;
  setEditTags: (v: string) => void;
  onClose: () => void;
  onSave: () => void;
  onDelete: () => void;
  onTrustDelta: (delta: number) => void;
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  t: any;
}

function FactDetailPanel({
  fact,
  loading,
  editContent,
  editCategory,
  editTags,
  saving,
  setEditContent,
  setEditCategory,
  setEditTags,
  onClose,
  onSave,
  onDelete,
  onTrustDelta,
  t,
}: FactDetailPanelProps) {
  return (
    <Card>
      <CardHeader className="py-3 px-4">
        <div className="flex items-center justify-between flex-wrap gap-2">
          <CardTitle className="text-sm flex items-center gap-2 min-w-0">
            <Button
              ghost
              size="xs"
              onClick={onClose}
              aria-label={t.skills?.backToList ?? "Back"}
            >
              <ArrowLeft />
            </Button>
            <Database className="h-4 w-4 shrink-0" />
            <span className="font-mono-ui">#{fact.fact_id}</span>
            <Badge tone="secondary" className="text-[10px]">
              trust {fact.trust_score?.toFixed?.(2) ?? fact.trust_score}
            </Badge>
          </CardTitle>
          <div className="flex items-center gap-2">
            <Button
              ghost
              size="sm"
              onClick={() => onTrustDelta(0.1)}
              disabled={saving}
              aria-label={t.memory?.trustUp ?? "Trust up"}
            >
              <TrendingUp />
            </Button>
            <Button
              ghost
              size="sm"
              onClick={() => onTrustDelta(-0.1)}
              disabled={saving}
              aria-label={t.memory?.trustDown ?? "Trust down"}
            >
              <TrendingDown />
            </Button>
            <Button onClick={onSave} disabled={saving} size="sm">
              <Save />
              {saving ? t.memory?.saving ?? "Saving..." : t.memory?.save ?? "Save"}
            </Button>
            <Button outlined destructive onClick={onDelete} disabled={saving} size="sm">
              <Trash2 />
              {t.memory?.delete ?? "Delete"}
            </Button>
          </div>
        </div>
      </CardHeader>
      <CardContent className="px-4 pb-4 flex flex-col gap-3">
        {loading ? (
          <div className="py-12 flex items-center justify-center">
            <Spinner className="text-2xl text-primary" />
          </div>
        ) : (
          <>
            <div className="grid gap-1 text-xs text-muted-foreground">
              <div>
                <span className="uppercase text-[9px] tracking-wider mr-1">
                  {t.memory?.retrievalCount ?? "Retrieved"}:
                </span>
                <span className="font-mono">{fact.retrieval_count}</span>
                <span className="mx-2 opacity-40">·</span>
                <span className="uppercase text-[9px] tracking-wider mr-1">
                  {t.memory?.helpfulCount ?? "Helpful"}:
                </span>
                <span className="font-mono">{fact.helpful_count}</span>
              </div>
              <div>
                <span className="uppercase text-[9px] tracking-wider mr-1">
                  {t.memory?.createdAt ?? "Created"}:
                </span>
                <span className="font-mono">{formatTime(fact.created_at)}</span>
                <span className="mx-2 opacity-40">·</span>
                <span className="uppercase text-[9px] tracking-wider mr-1">
                  {t.memory?.updatedAt ?? "Updated"}:
                </span>
                <span className="font-mono">{formatTime(fact.updated_at)}</span>
              </div>
              {fact.entities.length > 0 && (
                <div className="flex items-center gap-1 flex-wrap">
                  <span className="uppercase text-[9px] tracking-wider mr-1">
                    {t.memory?.entitiesTab ?? "Entities"}:
                  </span>
                  {fact.entities.map((e) => (
                    <Badge key={e.entity_id} tone="outline" className="text-[10px]">
                      {e.name}
                    </Badge>
                  ))}
                </div>
              )}
            </div>
            <textarea
              value={editContent}
              onChange={(e) => setEditContent(e.target.value)}
              disabled={saving}
              spellCheck={false}
              className="font-mono text-xs min-h-[200px] w-full p-3 border border-border bg-muted/10 outline-none focus:border-primary disabled:opacity-70"
            />
            <div className="grid gap-2 sm:grid-cols-2">
              <Input
                placeholder={t.memory?.categoryLabel ?? "Category"}
                value={editCategory}
                onChange={(e) => setEditCategory(e.target.value)}
                disabled={saving}
              />
              <Input
                placeholder={t.memory?.tagsLabel ?? "Tags"}
                value={editTags}
                onChange={(e) => setEditTags(e.target.value)}
                disabled={saving}
              />
            </div>
          </>
        )}
      </CardContent>
    </Card>
  );
}
