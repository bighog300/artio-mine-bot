import { useState } from "react";
import { Image } from "lucide-react";

interface ImageThumbnailProps {
  url: string;
  alt?: string;
  imageType?: string;
  className?: string;
}

export function ImageThumbnail({ url, alt, imageType, className }: ImageThumbnailProps) {
  const [error, setError] = useState(false);

  if (error) {
    return (
      <div className={`flex items-center justify-center bg-muted rounded ${className ?? "w-full h-full"}`}>
        <Image className="text-muted-foreground/80" size={24} />
      </div>
    );
  }

  return (
    <div className={`relative overflow-hidden rounded ${className ?? ""}`}>
      <img
        src={url}
        alt={alt ?? "Image"}
        className="w-full h-full object-cover"
        onError={() => setError(true)}
        loading="lazy"
      />
      {imageType && (
        <span className="absolute bottom-0 left-0 bg-black/60 text-white text-xs px-1 py-0.5 rounded-tr">
          {imageType}
        </span>
      )}
    </div>
  );
}
