import { useQuery } from "@tanstack/react-query";
import { Check } from "lucide-react";
import { getImages } from "@/lib/api";

interface ImageSelectionPanelProps {
  recordId: string;
  primaryImageId: string | null;
  onPrimarySet: (imageId: string) => void;
}

export function ImageSelectionPanel({
  recordId,
  primaryImageId,
  onPrimarySet,
}: ImageSelectionPanelProps) {
  const { data, isLoading } = useQuery({
    queryKey: ["record-images", recordId],
    queryFn: () => getImages({ record_id: recordId, limit: 100 }),
    enabled: Boolean(recordId),
  });

  const images = data?.items ?? [];
  const validCount = images.filter((image) => image.is_valid).length;

  if (isLoading) {
    return <div className="text-sm text-gray-500">Loading images…</div>;
  }

  if (images.length === 0) {
    return <div className="text-sm text-gray-500">No images collected for this record.</div>;
  }

  return (
    <div className="space-y-2">
      <div className="grid grid-cols-4 gap-2">
        {images.map((image) => (
          <button
            key={image.id}
            type="button"
            onClick={() => onPrimarySet(image.id)}
            className={`relative rounded-md overflow-hidden border text-left ${
              primaryImageId === image.id ? "border-blue-500" : "border-gray-200"
            } ${!image.is_valid ? "opacity-40" : "opacity-100"}`}
            title={image.url}
          >
            <img src={image.url} alt={image.alt_text ?? ""} className="h-20 w-20 object-cover" />
            {primaryImageId === image.id && (
              <span className="absolute top-1 right-1 h-5 w-5 rounded-full bg-blue-600 text-white flex items-center justify-center">
                <Check size={12} />
              </span>
            )}
          </button>
        ))}
      </div>
      <div className="text-xs text-gray-500">{images.length} images · {validCount} valid</div>
    </div>
  );
}
