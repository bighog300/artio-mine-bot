import { useMemo, useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { useNavigate } from "react-router-dom";
import { Globe, Sparkles, Wand2 } from "lucide-react";
import { Alert, Button, EmptyState, Input, Skeleton, useToast } from "@/components/ui";
import { getSmartMineTemplates, startSmartMine } from "@/lib/api";

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

  return (
    <div className="mx-auto w-full max-w-5xl space-y-6">
      <div className="space-y-2">
        <h1 className="text-2xl font-bold text-foreground lg:text-3xl">Smart Mining</h1>
        <p className="text-sm text-muted-foreground lg:text-base">
          Paste an art site URL, choose an extraction template, and let Smart Mode run the setup automatically.
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
            hint="Include the homepage or a section page you want Smart Mode to analyze."
            required
          />

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
    </div>
  );
}
