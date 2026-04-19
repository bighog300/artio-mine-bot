import { useEffect, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { getSettings, saveSettings, testArtioConnection } from "@/lib/api";
import { cn } from "@/lib/utils";
import { Alert, Button, Input, useToast } from "@/components/ui";

// ── Connection status union ───────────────────────────────────────────────────

type ConnectionStatus =
  | { state: "idle" }
  | { state: "testing" }
  | { state: "success"; message: string }
  | { state: "error"; message: string };

// ── Page component ────────────────────────────────────────────────────────────

export function Settings() {
  const queryClient = useQueryClient();
  const toast = useToast();
  const { data, isLoading } = useQuery({ queryKey: ["settings"], queryFn: getSettings });

  // Artio API section
  const [artioUrl, setArtioUrl] = useState("");
  const [artioKey, setArtioKey] = useState("");
  const [artioKeyDirty, setArtioKeyDirty] = useState(false);
  const [openaiKey, setOpenaiKey] = useState("");
  const [openaiKeyDirty, setOpenaiKeyDirty] = useState(false);
  const [connStatus, setConnStatus] = useState<ConnectionStatus>({ state: "idle" });

  // Crawl settings section
  const [maxDepth, setMaxDepth] = useState(3);
  const [maxPages, setMaxPages] = useState(500);
  const [crawlDelay, setCrawlDelay] = useState(1000);

  const [savedAt, setSavedAt] = useState<number | null>(null);

  // Populate form once settings are loaded
  useEffect(() => {
    if (!data) return;
    setArtioUrl(data.artio_api_url ?? "");
    setArtioKey(data.artio_api_key_masked ?? "");
    setOpenaiKey(data.openai_api_key_masked ?? "");
    setMaxDepth(data.max_crawl_depth);
    setMaxPages(data.max_pages_per_source);
    setCrawlDelay(data.crawl_delay_ms);
  }, [data]);

  const saveMutation = useMutation({
    mutationFn: () =>
      saveSettings({
        artio_api_url: artioUrl || null,
        // Only send the key when the user has actually typed a new value
        ...(artioKeyDirty ? { artio_api_key: artioKey || null } : {}),
        ...(openaiKeyDirty ? { openai_api_key: openaiKey || null } : {}),
        max_crawl_depth: maxDepth,
        max_pages_per_source: maxPages,
        crawl_delay_ms: crawlDelay,
      }),
    onMutate: () => toast.loading("Saving settings..."),
    onSuccess: (updated) => {
      toast.success("Settings saved");
      queryClient.setQueryData(["settings"], updated);
      setArtioKeyDirty(false);
      setOpenaiKeyDirty(false);
      setArtioKey(updated.artio_api_key_masked ?? "");
      setOpenaiKey(updated.openai_api_key_masked ?? "");
      setSavedAt(Date.now());
    },
    onError: (error: Error) => toast.error("Failed to save settings", error.message),
  });

  const testMutation = useMutation({
    onMutate: () => {
      toast.loading("Testing Artio connection...");
      setConnStatus({ state: "testing" });
    },
    mutationFn: testArtioConnection,
    onSuccess: (result) => {
      if (result.success) {
        toast.success("Connection successful", result.message);
      } else {
        toast.error("Connection failed", result.message);
      }
      setConnStatus(
        result.success
          ? { state: "success", message: result.message }
          : { state: "error", message: result.message }
      );
    },
    onError: (e: Error) => {
      setConnStatus({ state: "error", message: e.message });
      toast.error("Connection test failed", e.message);
    },
  });

  if (isLoading) {
    return <div className="p-4 text-muted-foreground/80 text-sm">Loading settings…</div>;
  }

  return (
    <div className="space-y-4 lg:space-y-6">
      <h1 className="text-2xl lg:text-3xl font-bold text-foreground">Settings</h1>

      {/* ── Warning banner ─────────────────────────────────────────────────── */}
      {!data?.artio_configured && (
        <Alert
          variant="warning"
          title="Artio API not configured"
          description="Set ARTIO_API_URL and ARTIO_API_KEY below to enable export."
        />
      )}
      {!data?.openai_configured && (
        <Alert
          variant="warning"
          title="OpenAI key not configured"
          description="Add OPENAI_API_KEY below to enable mining."
        />
      )}

      {/* ── Artio API card ──────────────────────────────────────────────────── */}
      <div className="rounded-lg border bg-card">
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2 border-b p-4">
          <div>
            <h2 className="font-semibold text-foreground">Artio API</h2>
            <p className="mt-0.5 text-xs text-muted-foreground">
              Connection settings for Artio export
            </p>
          </div>
          <ConnectionBadge status={connStatus} />
        </div>

        <div className="space-y-4 p-4">
          <Field label="API URL" hint="e.g. https://api.artio.io">
            <Input
              type="url"
              value={artioUrl}
              onChange={(e) => setArtioUrl(e.target.value)}
              placeholder="https://api.artio.io"
              className={inputCls}
            />
          </Field>

          <Field
            label="API Key"
            hint="Your key is masked after saving. Enter a new value to rotate it."
          >
            <Input
              type="password"
              value={artioKey}
              onChange={(e) => {
                setArtioKey(e.target.value);
                setArtioKeyDirty(true);
              }}
              placeholder="sk-…"
              className={inputCls}
            />
          </Field>

          <Field
            label="OpenAI API Key"
            hint="Used by the mining pipeline. Your key is masked after saving."
          >
            <Input
              type="password"
              value={openaiKey}
              onChange={(e) => {
                setOpenaiKey(e.target.value);
                setOpenaiKeyDirty(true);
              }}
              placeholder="sk-…"
              className={inputCls}
            />
          </Field>

          <div className="pt-1">
            <Button
              onClick={() => testMutation.mutate()}
              disabled={!artioUrl || testMutation.isPending}
              variant="secondary"
            >
              {testMutation.isPending ? "Testing…" : "Test Connection"}
            </Button>
          </div>
        </div>
      </div>

      {/* ── Crawl settings card ─────────────────────────────────────────────── */}
      <div className="rounded-lg border bg-card">
        <div className="border-b p-4">
          <h2 className="font-semibold text-foreground">Crawl Settings</h2>
          <p className="mt-0.5 text-xs text-muted-foreground">
            Controls how deeply and quickly the crawler operates
          </p>
        </div>

        <div className="space-y-4 p-4">
          <Field label="Max Crawl Depth" hint="How many link-levels deep to follow (1–10)">
            <Input
              type="number"
              min={1}
              max={10}
              value={maxDepth}
              onChange={(e) => setMaxDepth(Number(e.target.value))}
              className={inputCls}
            />
          </Field>

          <Field
            label="Max Pages per Source"
            hint="Hard cap on pages crawled in a single source run"
          >
            <Input
              type="number"
              min={1}
              max={5000}
              value={maxPages}
              onChange={(e) => setMaxPages(Number(e.target.value))}
              className={inputCls}
            />
          </Field>

          <Field
            label="Crawl Delay (ms)"
            hint="Minimum milliseconds between requests to the same domain"
          >
            <Input
              type="number"
              min={0}
              max={30000}
              value={crawlDelay}
              onChange={(e) => setCrawlDelay(Number(e.target.value))}
              className={inputCls}
            />
          </Field>
        </div>
      </div>

      {/* ── Save row ────────────────────────────────────────────────────────── */}
      <div className="flex items-center gap-3">
        <Button
          onClick={() => saveMutation.mutate()}
          disabled={saveMutation.isPending}
        >
          {saveMutation.isPending ? "Saving…" : "Save Settings"}
        </Button>

        {savedAt && Date.now() - savedAt < 3000 && (
          <span className="text-sm font-medium text-green-600">✓ Saved</span>
        )}
        {saveMutation.isError && (
          <span className="text-sm text-red-600">Failed to save — check the console</span>
        )}
      </div>
    </div>
  );
}

// ── Sub-components ────────────────────────────────────────────────────────────

const inputCls =
  "w-full rounded-md border border-border px-3 py-2 text-sm focus:border-transparent focus:ring-2 focus:ring-blue-500";

function Field({
  label,
  hint,
  children,
}: {
  label: string;
  hint?: string;
  children: React.ReactNode;
}) {
  return (
    <div>
      <label className="mb-1 block text-sm font-medium text-muted-foreground">{label}</label>
      {children}
      {hint && <p className="mt-1 text-xs text-muted-foreground/80">{hint}</p>}
    </div>
  );
}

function ConnectionBadge({ status }: { status: ConnectionStatus }) {
  if (status.state === "idle") return null;

  const cfg: Record<Exclude<ConnectionStatus["state"], "idle">, { cls: string; label: string }> = {
    testing: { cls: "bg-muted text-muted-foreground animate-pulse", label: "Testing…" },
    success: { cls: "bg-green-100 text-green-800", label: "Connected" },
    error: { cls: "bg-red-100 text-red-800", label: "Error" },
  };

  const { cls, label } = cfg[status.state];
  const detail = "message" in status ? status.message : undefined;

  return (
    <span
      className={cn("inline-flex items-center gap-1 rounded px-2 py-0.5 text-xs font-medium", cls)}
      title={detail}
    >
      {label}
      {detail && <span className="opacity-70">— {detail}</span>}
    </span>
  );
}
