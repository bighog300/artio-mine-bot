import { useMemo, useState } from "react";
import { Alert, Button, Checkbox, Input, TextArea } from "@/components/ui";

export type GuidedModePayload = {
  site_type: string;
  entity_types: string[];
  fields: Array<{
    key: string;
    label: string;
    required: boolean;
    selector: string;
    fallback_selectors: string[];
  }>;
  selector_samples: string[];
};

type WizardStep = 1 | 2 | 3 | 4 | 5;

const SITE_TYPES = [
  { key: "art_gallery", label: "Art gallery" },
  { key: "event_calendar", label: "Event calendar" },
  { key: "museum_collection", label: "Museum collection" },
  { key: "artist_directory", label: "Artist directory" },
  { key: "publication", label: "Art publication" },
];

const ENTITY_TYPES = [
  { key: "artists", label: "Artists" },
  { key: "events", label: "Events" },
  { key: "venues", label: "Venues" },
  { key: "exhibitions", label: "Exhibitions" },
  { key: "artworks", label: "Artworks" },
];

type FieldConfig = {
  key: string;
  label: string;
  required: boolean;
  enabled: boolean;
  selector: string;
  fallback_selectors: string[];
};

const COMMON_FIELDS: FieldConfig[] = [
  {
    key: "title",
    label: "Title",
    required: true,
    enabled: true,
    selector: "h1, .title, .entry-title",
    fallback_selectors: ["h2", "[data-title]"],
  },
  {
    key: "description",
    label: "Description",
    required: false,
    enabled: true,
    selector: ".description, .summary, article p",
    fallback_selectors: [".content p:first-of-type", "meta[name='description']"],
  },
  {
    key: "date",
    label: "Date",
    required: false,
    enabled: true,
    selector: "time, .date, .event-date",
    fallback_selectors: ["[datetime]", ".meta time"],
  },
  {
    key: "location",
    label: "Location",
    required: false,
    enabled: true,
    selector: ".location, .venue, [itemprop='location']",
    fallback_selectors: ["address", ".event-location"],
  },
];

const SAMPLE_DOCS = [
  `<main><article><h1 class='title'>Open Studio Night</h1><p class='description'>A group show with live demos.</p><time class='date'>May 5, 2026</time><p class='location'>Warehouse District</p></article></main>`,
  `<main><article><h1 class='entry-title'>Spring Salon</h1><p class='summary'>Contemporary painting and sculpture.</p><div class='event-date'>April 28, 2026</div><p class='venue'>City Gallery</p></article></main>`,
  `<main><section><h1>Artist Talk: Maya Lane</h1><article><p>Join us for an evening conversation.</p><time datetime='2026-05-12'>May 12</time><address>Riverfront Arts Center</address></article></section></main>`,
  `<main><article><h1 class='title'>Collectors Preview</h1><p class='description'>Preview of new acquisitions.</p><p class='date'>June 1, 2026</p><p class='location'>West Hall</p></article></main>`,
  `<main><article><h1 class='title'>Summer Residency Showcase</h1><p class='summary'>Resident artists present final works.</p><time class='date'>July 10, 2026</time><div class='location'>Artio Pavilion</div></article></main>`,
];

function parseElements(html: string): Array<{ label: string; selector: string; text: string }> {
  const parser = new DOMParser();
  const doc = parser.parseFromString(html, "text/html");
  const candidates = Array.from(doc.querySelectorAll("h1, h2, h3, p, time, address, span, div"))
    .map((el) => {
      const className = (el.getAttribute("class") || "").trim().split(/\s+/).filter(Boolean)[0];
      const selector = className ? `${el.tagName.toLowerCase()}.${className}` : el.tagName.toLowerCase();
      return {
        label: `${el.tagName.toLowerCase()}${className ? `.${className}` : ""}`,
        selector,
        text: (el.textContent || "").trim(),
      };
    })
    .filter((entry) => entry.text.length > 0)
    .slice(0, 12);
  return candidates;
}

function resolveSelector(html: string, selector: string): string | null {
  try {
    const parser = new DOMParser();
    const doc = parser.parseFromString(html, "text/html");
    const target = doc.querySelector(selector);
    return target?.textContent?.trim() || null;
  } catch {
    return null;
  }
}

interface GuidedModeWizardProps {
  url: string;
  saving: boolean;
  onSave: (payload: GuidedModePayload) => void;
}

export function GuidedModeWizard({ url, saving, onSave }: GuidedModeWizardProps) {
  const [step, setStep] = useState<WizardStep>(1);
  const [siteType, setSiteType] = useState<string>(SITE_TYPES[0].key);
  const [entityTypes, setEntityTypes] = useState<string[]>(["artists", "events"]);
  const [fields, setFields] = useState<FieldConfig[]>(COMMON_FIELDS);
  const [customFieldName, setCustomFieldName] = useState("");
  const [selectedFieldKey, setSelectedFieldKey] = useState<string>(COMMON_FIELDS[0].key);
  const [manualSelector, setManualSelector] = useState<string>(COMMON_FIELDS[0].selector);

  const selectedField = useMemo(() => fields.find((field) => field.key === selectedFieldKey), [fields, selectedFieldKey]);
  const selectorPreview = useMemo(
    () => SAMPLE_DOCS.map((sample) => resolveSelector(sample, manualSelector)).filter((item) => item),
    [manualSelector],
  );

  const sampleElements = useMemo(() => parseElements(SAMPLE_DOCS[0]), []);
  const confidence = selectorPreview.length >= 4 ? "high" : selectorPreview.length >= 2 ? "medium" : "low";

  const canContinue =
    (step === 1 && Boolean(siteType)) ||
    (step === 2 && entityTypes.length > 0) ||
    (step === 3 && fields.some((field) => field.enabled)) ||
    step === 4 ||
    step === 5;

  const updateField = (fieldKey: string, patch: Partial<FieldConfig>) => {
    setFields((prev) => prev.map((field) => (field.key === fieldKey ? { ...field, ...patch } : field)));
  };

  const addCustomField = () => {
    const key = customFieldName.trim().toLowerCase().replace(/\s+/g, "_");
    if (!key || fields.some((field) => field.key === key)) {
      return;
    }
    setFields((prev) => [
      ...prev,
      { key, label: customFieldName.trim(), enabled: true, required: false, selector: "", fallback_selectors: [] },
    ]);
    setCustomFieldName("");
  };

  const applySelectorToField = () => {
    if (!selectedField) return;
    updateField(selectedField.key, {
      selector: manualSelector,
      fallback_selectors: selectedField.fallback_selectors.length ? selectedField.fallback_selectors : [".content", "article p"],
    });
  };

  const goNext = () => setStep((prev) => (prev < 5 ? ((prev + 1) as WizardStep) : prev));
  const goBack = () => setStep((prev) => (prev > 1 ? ((prev - 1) as WizardStep) : prev));

  const completeWizard = () => {
    onSave({
      site_type: siteType,
      entity_types: entityTypes,
      selector_samples: SAMPLE_DOCS,
      fields: fields
        .filter((field) => field.enabled)
        .map((field) => ({
          key: field.key,
          label: field.label,
          required: field.required,
          selector: field.selector,
          fallback_selectors: field.fallback_selectors,
        })),
    });
  };

  return (
    <section aria-label="Guided mode wizard" className="rounded-lg border bg-card p-4 lg:p-6">
      <div className="mb-4 flex items-center justify-between gap-3">
        <div>
          <h2 className="text-lg font-semibold text-foreground">Guided Mode Wizard</h2>
          <p className="text-sm text-muted-foreground">Step {step} of 5 — setup with plain language and previews.</p>
        </div>
        <div className="h-2 w-32 overflow-hidden rounded-full bg-muted" aria-hidden>
          <div className="h-full bg-primary transition-all" style={{ width: `${(step / 5) * 100}%` }} />
        </div>
      </div>

      {step === 1 ? (
        <div className="space-y-3">
          <p className="text-sm text-muted-foreground">Choose what kind of site this is so we can preload sensible defaults.</p>
          <div className="grid gap-2 md:grid-cols-2">
            {SITE_TYPES.map((type) => (
              <button
                key={type.key}
                type="button"
                onClick={() => setSiteType(type.key)}
                className={`rounded-md border p-3 text-left ${siteType === type.key ? "border-primary bg-primary/5" : "border-border"}`}
                aria-pressed={siteType === type.key}
              >
                <p className="font-medium text-foreground">{type.label}</p>
              </button>
            ))}
          </div>
        </div>
      ) : null}

      {step === 2 ? (
        <div className="space-y-3">
          <p className="text-sm text-muted-foreground">Select the entity types to extract.</p>
          <div className="grid gap-2 md:grid-cols-3">
            {ENTITY_TYPES.map((entity) => (
              <Checkbox
                key={entity.key}
                id={`entity-${entity.key}`}
                label={entity.label}
                checked={entityTypes.includes(entity.key)}
                onChange={(checked) => {
                  setEntityTypes((prev) =>
                    checked ? [...new Set([...prev, entity.key])] : prev.filter((item) => item !== entity.key),
                  );
                }}
              />
            ))}
          </div>
        </div>
      ) : null}

      {step === 3 ? (
        <div className="space-y-4">
          <p className="text-sm text-muted-foreground">Common fields are pre-filled. Enable what you need and add custom fields.</p>
          <div className="space-y-3">
            {fields.map((field) => (
              <div key={field.key} className="rounded-md border p-3">
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <Checkbox
                    id={`field-enabled-${field.key}`}
                    label={field.label}
                    checked={field.enabled}
                    onChange={(checked) => updateField(field.key, { enabled: checked })}
                  />
                  <Checkbox
                    id={`field-required-${field.key}`}
                    label="Required"
                    checked={field.required}
                    onChange={(checked) => updateField(field.key, { required: checked })}
                    disabled={!field.enabled}
                  />
                </div>
                <p className="mt-2 text-xs text-muted-foreground">Primary selector: {field.selector || "Not set"}</p>
              </div>
            ))}
          </div>
          <div className="rounded-md border p-3">
            <Input
              label="Add custom field"
              placeholder="e.g. curator, ticket_price"
              value={customFieldName}
              onChange={(event) => setCustomFieldName(event.target.value)}
            />
            <div className="mt-2">
              <Button variant="outline" size="sm" onClick={addCustomField}>Add field</Button>
            </div>
          </div>
        </div>
      ) : null}

      {step === 4 ? (
        <div className="space-y-4">
          <p className="text-sm text-muted-foreground">Select a field, click a sample element, or edit the selector manually.</p>
          <div className="grid gap-4 lg:grid-cols-2">
            <div className="space-y-3">
              <label className="block text-sm font-medium text-foreground" htmlFor="guided-field-select">Field</label>
              <select
                id="guided-field-select"
                className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
                value={selectedFieldKey}
                onChange={(event) => {
                  const value = event.target.value;
                  setSelectedFieldKey(value);
                  const field = fields.find((item) => item.key === value);
                  setManualSelector(field?.selector || "");
                }}
              >
                {fields.filter((field) => field.enabled).map((field) => (
                  <option key={field.key} value={field.key}>{field.label}</option>
                ))}
              </select>

              <div className="rounded-md border p-3">
                <p className="mb-2 text-sm font-medium text-foreground">Sample page (iframe preview)</p>
                <iframe title="Sample page preview" className="h-48 w-full rounded border" srcDoc={SAMPLE_DOCS[0]} />
              </div>

              <div className="rounded-md border p-3">
                <p className="mb-2 text-sm font-medium text-foreground">Clickable element suggestions</p>
                <div className="flex flex-wrap gap-2">
                  {sampleElements.map((el) => (
                    <button
                      key={`${el.selector}-${el.text}`}
                      type="button"
                      onClick={() => setManualSelector(el.selector)}
                      className="rounded border px-2 py-1 text-xs hover:border-primary"
                    >
                      {el.label}
                    </button>
                  ))}
                </div>
              </div>
            </div>

            <div className="space-y-3">
              <Input
                label="CSS selector"
                value={manualSelector}
                onChange={(event) => setManualSelector(event.target.value)}
                hint="You can edit this manually."
              />
              <Button variant="outline" onClick={applySelectorToField}>Apply selector to field</Button>

              <div className="rounded-md border p-3">
                <p className="text-sm font-medium text-foreground">Test on 5 samples</p>
                <ul className="mt-2 space-y-2 text-sm">
                  {SAMPLE_DOCS.map((sample, index) => (
                    <li key={index} className="rounded border p-2">
                      <span className="font-medium">Sample {index + 1}:</span>{" "}
                      {resolveSelector(sample, manualSelector) || <span className="text-muted-foreground">No match</span>}
                    </li>
                  ))}
                </ul>
              </div>

              <Alert
                variant={confidence === "low" ? "warning" : "info"}
                title={confidence === "low" ? "Low confidence selector" : "Selector confidence looks okay"}
                description={`Matched ${selectorPreview.length} of 5 sample pages. Add fallback selectors if needed.`}
              />
            </div>
          </div>
        </div>
      ) : null}

      {step === 5 ? (
        <div className="space-y-4">
          <p className="text-sm text-muted-foreground">Preview what will be extracted before saving.</p>
          <div className="rounded-md border p-3">
            <p className="text-sm"><span className="font-medium">URL:</span> {url || "Not set"}</p>
            <p className="text-sm"><span className="font-medium">Site type:</span> {siteType}</p>
            <p className="text-sm"><span className="font-medium">Entity types:</span> {entityTypes.join(", ")}</p>
          </div>
          <div className="space-y-2">
            {fields.filter((field) => field.enabled).map((field) => {
              const matched = resolveSelector(SAMPLE_DOCS[0], field.selector);
              const fieldConfidence = matched ? "ok" : "low";
              return (
                <div key={field.key} className="rounded-md border p-3">
                  <div className="flex items-center justify-between">
                    <p className="font-medium text-foreground">{field.label}</p>
                    {fieldConfidence === "low" ? (
                      <span className="text-xs font-medium text-amber-700">Low confidence</span>
                    ) : (
                      <span className="text-xs font-medium text-emerald-700">Matched</span>
                    )}
                  </div>
                  <p className="text-xs text-muted-foreground">Selector: {field.selector || "Not set"}</p>
                  <p className="mt-1 text-sm">Preview value: {matched || "No preview value"}</p>
                </div>
              );
            })}
          </div>

          <TextArea
            label="Quick notes (optional)"
            placeholder="Example: prioritize event detail pages first."
            rows={3}
            disabled
            hint="Notes support is coming soon."
          />
        </div>
      ) : null}

      <div className="mt-6 flex flex-col gap-2 sm:flex-row sm:justify-between">
        <Button variant="outline" onClick={goBack} disabled={step === 1}>Back</Button>
        <div className="flex gap-2">
          {step < 5 ? (
            <Button onClick={goNext} disabled={!canContinue}>Continue</Button>
          ) : (
            <Button onClick={completeWizard} loading={saving}>Save configuration</Button>
          )}
        </div>
      </div>
    </section>
  );
}
