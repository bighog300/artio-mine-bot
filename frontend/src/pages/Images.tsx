import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { getImages, getSources } from "@/lib/api";
import { ImageThumbnail } from "@/components/shared/ImageThumbnail";

export function Images() {
  const [sourceId, setSourceId] = useState("");
  const [imageType, setImageType] = useState("");
  const [validOnly, setValidOnly] = useState(true);

  const { data: sources } = useQuery({ queryKey: ["sources"], queryFn: getSources });
  const { data, isLoading } = useQuery({
    queryKey: ["images", { sourceId, imageType, validOnly }],
    queryFn: () =>
      getImages({
        source_id: sourceId || undefined,
        image_type: imageType || undefined,
        is_valid: validOnly ? true : undefined,
        limit: 100,
      }),
  });

  return (
    <div className="space-y-4">
      <h1 className="text-2xl font-bold text-gray-900">Images</h1>

      <div className="flex gap-3 flex-wrap">
        <select
          value={sourceId}
          onChange={(e) => setSourceId(e.target.value)}
          className="border border-gray-300 rounded px-2 py-1.5 text-sm"
        >
          <option value="">All sources</option>
          {sources?.items.map((s) => (
            <option key={s.id} value={s.id}>{s.name ?? s.url}</option>
          ))}
        </select>
        <select
          value={imageType}
          onChange={(e) => setImageType(e.target.value)}
          className="border border-gray-300 rounded px-2 py-1.5 text-sm"
        >
          <option value="">All types</option>
          {["profile", "artwork", "poster", "venue", "unknown"].map((t) => (
            <option key={t} value={t}>{t}</option>
          ))}
        </select>
        <label className="flex items-center gap-2 text-sm">
          <input
            type="checkbox"
            checked={validOnly}
            onChange={(e) => setValidOnly(e.target.checked)}
            className="rounded"
          />
          Valid only
        </label>
      </div>

      {isLoading && <div className="text-gray-400 text-center py-8">Loading...</div>}

      <div className="columns-2 md:columns-3 lg:columns-4 gap-3 space-y-3">
        {data?.items.map((img) => (
          <div key={img.id} className="break-inside-avoid rounded overflow-hidden border bg-white group relative">
            <ImageThumbnail
              url={img.url}
              alt={img.alt_text ?? ""}
              imageType={img.image_type}
              className="w-full"
            />
            <div className="absolute inset-0 bg-black/70 opacity-0 group-hover:opacity-100 transition-opacity p-2 text-white text-xs space-y-1 flex flex-col justify-end">
              <div className="font-medium">{img.image_type}</div>
              <div>{img.confidence}% confidence</div>
              {img.alt_text && <div className="truncate opacity-75">{img.alt_text}</div>}
            </div>
          </div>
        ))}
      </div>

      {!isLoading && data?.items.length === 0 && (
        <div className="text-center text-gray-400 py-12">No images found.</div>
      )}
    </div>
  );
}
