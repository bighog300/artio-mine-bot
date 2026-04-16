import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { MobileCard, MobileCardRow } from "@/components/ui/MobileCard";
import { Select } from "@/components/ui/Select";
import { useIsMobile, useViewport } from "@/lib/mobile-utils";

export function MobileTest() {
  const isMobile = useIsMobile();
  const viewport = useViewport();

  return (
    <div className="space-y-6">
      <div>
        <h1 className="mb-2 text-2xl font-bold text-foreground lg:text-3xl">Mobile Test Page</h1>
        <p className="text-sm text-muted-foreground">
          Device: {isMobile ? "Mobile" : "Desktop"} | Viewport: {viewport.width}x{viewport.height}
        </p>
      </div>

      <section className="space-y-4">
        <h2 className="text-lg font-semibold">Buttons</h2>
        <div className="space-y-2">
          <Button fullWidth variant="primary">
            Full Width Primary
          </Button>
          <Button fullWidth variant="secondary">
            Full Width Secondary
          </Button>
          <div className="flex gap-2">
            <Button className="flex-1">Half</Button>
            <Button className="flex-1">Half</Button>
          </div>
        </div>
      </section>

      <section className="space-y-4">
        <h2 className="text-lg font-semibold">Form Elements</h2>
        <Input label="Email" type="email" placeholder="you@example.com" />
        <Select
          label="Country"
          options={[
            { value: "us", label: "United States" },
            { value: "uk", label: "United Kingdom" },
          ]}
        />
      </section>

      <section className="space-y-4">
        <h2 className="text-lg font-semibold">Mobile Cards</h2>
        <MobileCard>
          <MobileCardRow label="Name" value="John Doe" />
          <MobileCardRow label="Email" value="john@example.com" />
          <MobileCardRow label="Status" value={<span className="text-green-600">Active</span>} />
        </MobileCard>
      </section>
    </div>
  );
}
