import { useMemo, useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { useNavigate } from "react-router-dom";
import { Globe, Sparkles, Wand2 } from "lucide-react";
import { Alert, Button, EmptyState, Input, Skeleton, useToast } from "@/components/ui";
import { createSource, getSmartMineTemplates, startSmartMine, updateSource } from "@/lib/api";
import { GuidedModePayload, GuidedModeWizard } from "@/components/smart-mining/GuidedModeWizard";

function normalizeUrl(raw: string): string {
  const trimmed = raw.trim();
  if (!trimmed) return "";

  if (/^https?:\/\//i.test(trimmed)) {
    return trimmed;
  }

  return `https://${trimmed}`;
}

function validateUrl(raw: string): string | null {
  const normalized = normalizeUrl(raw);
  if (!normalized) {
    return "Please enter a URL.";
  }

  try {
    const parsed = new URL(normalized);
    if (!parsed.hostname || !parsed.protocol.startsWith("http")) {
      return "Please enter a valid http(s) URL.";
    }
  } catch {
    return "Please enter a valid URL.";
  }

  return null;
}

export function SmartMining() {
  const [url, setUrl] = useState("");
  const [selectedTemplateId, setSelectedTemplateId] = useState<string | undefined>(undefined);
  const [urlError, setUrlError] = useState<string | null>(null);
  const [mode, setMode] = useState<"smart" | "guided">("smart");
  const navigate = useNavigate();
  const toast = useToast();

  const templatesQuery = useQuery({
    queryKey: ["smart-mine-templates"],
    queryFn: getSmartMineTemplates,
  });

  const startMutation = useMutation({
    mutationFn: startSmartMine,
    onMutate: () => ({ toastId: toast.loading("Starting smart mining...") }),
    onSuccess: (data, _vars, ctx) => {
      if (ctx?.toastId) toast.dismiss(ctx.toastId);
      toast.success("Smart mining started");
      navigate(`/smart-mine/${data.source_id}/progress`);
    },
    onError: (error: Error, _vars, ctx) => {
      if (ctx?.toastId) toast.dismiss(ctx.toastId);
      toast.error("Could not start smart mining", error.message);
    },
    onSettled: (_data, _error, _vars, ctx) => {
      if (ctx?.toastId) toast.dismiss(ctx.toastId);
    },
  });

  const saveGuidedConfigMutation = useMutation({
    mutationFn: async (payload: GuidedModePayload) => {
      const normalized = normalizeUrl(url);
      const source = await createSource({
        url: normalized,
        name: `Guided - ${new URL(normalized).hostname}`,
        extraction_rules: {
          guided_mode: payload,
        },
        crawl_hints: {
          guided_mode_enabled: true,
          site_type: payload.site_type,
          entity_types: payload.entity_types,
        },
      });
      await updateSource(source.id, {
        extraction_rules: {
          guided_mode: payload,
        },
      });
      return source;
    },
    onMutate: () => ({ toastId: toast.loading("Saving Guided Mode configuration...") }),
    onSuccess: (source, _vars, ctx) => {
      if (ctx?.toastId) toast.dismiss(ctx.toastId);
      toast.success("Guided Mode configuration saved", "Starting mining with your saved setup.");
      navigate(`/sources/${source.id}/mapping`);
    },
    onError: (error: Error, _vars, ctx) => {
      if (ctx?.toastId) toast.dismiss(ctx.toastId);
      toast.error("Could not save Guided Mode config", error.message);
    },
    onSettled: (_data, _error, _vars, ctx) => {
      if (ctx?.toastId) toast.dismiss(ctx.toastId);
    },
  });

  const canSubmit = useMemo(() => !validateUrl(url) && !startMutation.isPending, [url, startMutation.isPending]);

  const handleStart = () => {
    const validationError = validateUrl(url);
    setUrlError(validationError);
    if (validationError) {
      return;
    }

    startMutation.mutate({
      url: normalizeUrl(url),
      template_id: selectedTemplateId,
    });
  };

  const handleSaveGuidedConfig = (payload: GuidedModePayload) => {
    const validationError = validateUrl(url);
    setUrlError(validationError);
    if (validationError) {
      return;
    }
    saveGuidedConfigMutation.mutate(payload);
  };

  return (
    <div className="mx-auto w-full max-w-5xl space-y-6">
      <div className="space-y-2">
        <h1 className="text-2xl font-bold text-foreground lg:text-3xl">Smart Mining</h1>
        <p className="text-sm text-muted-foreground lg:text-base">
          Choose Smart Mode for automatic setup or Guided Mode for a step-by-step visual wizard.
        </p>
      </div>

      <section className="rounded-lg border bg-card p-4 lg:p-6">
        <div className="space-y-4">
          <Input
            label="Website URL"
            placeholder="https://example.com"
            value={url}
            onChange={(event) => {
              setUrl(event.target.value);
              if (urlError) {
                setUrlError(null);
              }
            }}
            error={urlError ?? undefined}
            hint="Include the homepage or a section page you want to analyze."
            required
          />

          <div className="flex flex-wrap gap-2" role="tablist" aria-label="Mining setup mode">
            <Button variant={mode === "smart" ? "primary" : "outline"} onClick={() => setMode("smart")}>Smart Mode</Button>
            <Button variant={mode === "guided" ? "primary" : "outline"} onClick={() => setMode("guided")}>Guided Mode</Button>
          </div>
        </div>
      </section>

      {mode === "smart" ? (
        <section className="rounded-lg border bg-card p-4 lg:p-6">
          <div className="space-y-4">
            {templatesQuery.isLoading ? (
              <div className="grid gap-3 md:grid-cols-2">
                {Array.from({ length: 4 }).map((_, index) => (
                  <Skeleton key={index} className="h-32 rounded-lg border" />
                ))}
              </div>
            ) : templatesQuery.isError ? (
              <Alert
                variant="error"
                title="Could not load templates"
                description={templatesQuery.error instanceof Error ? templatesQuery.error.message : "Please try again."}
              />
            ) : (templatesQuery.data?.items.length ?? 0) > 0 ? (
              <div className="space-y-2">
                <p className="text-sm font-medium text-foreground">Template</p>
                <div className="grid gap-3 md:grid-cols-2">
                  {templatesQuery.data?.items.map((template) => {
                    const isSelected = selectedTemplateId === template.id;
                    return (
                      <button
                        key={template.id}
                        type="button"
                        onClick={() => setSelectedTemplateId(template.id)}
                        className={`rounded-lg border p-4 text-left transition ${
                          isSelected
                            ? "border-primary bg-primary/5 ring-2 ring-primary/30"
                            : "border-border bg-background hover:border-primary/50"
                        }`}
                      >
                        <div className="flex items-start justify-between gap-3">
                          <div>
                            <p className="font-semibold text-foreground">{template.name}</p>
                            <p className="mt-1 text-sm text-muted-foreground">{template.description ?? "No description provided."}</p>
                          </div>
                          <Wand2 className="h-4 w-4 shrink-0 text-muted-foreground" />
                        </div>
                      </button>
                    );
                  })}
                </div>
              </div>
            ) : (
              <EmptyState
                icon={Sparkles}
                title="No templates available"
                description="You can still start Smart Mining without a template."
              />
            )}

            <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
              <div className="flex items-center gap-2 text-sm text-muted-foreground">
                <Globe className="h-4 w-4" />
                Smart Mode will analyze and configure mining automatically.
              </div>
              <Button onClick={handleStart} loading={startMutation.isPending} disabled={!canSubmit} className="w-full sm:w-auto">
                Start Smart Mining
              </Button>
            </div>
          </div>
        </section>
      ) : (
        <GuidedModeWizard
          url={url}
          saving={saveGuidedConfigMutation.isPending}
          onSave={handleSaveGuidedConfig}
        />
      )}
    </div>
  );
}
