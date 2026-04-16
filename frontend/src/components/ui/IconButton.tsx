import { Button } from "@/components/ui/Button";
import type { IconButtonProps } from "@/types/ui";

export function IconButton({ className, size = "md", variant = "ghost", ...props }: IconButtonProps) {
  return (
    <Button
      {...props}
      variant={variant}
      size={size}
      className={className}
    />
  );
}
