import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import { MemoryRouter, Route, Routes, useLocation } from "react-router-dom";
import { describe, expect, it } from "vitest";

import { MappingReview } from "@/pages/MappingReview";

function renderPage() {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  function MappingPageProbe() {
    const location = useLocation();
    return <div>Source Mapping Workflow {location.search}</div>;
  }

  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={["/sources/src-1/mappings/map-1/review"]}>
        <Routes>
          <Route path="/sources/:id/mappings/:mappingId/review" element={<MappingReview />} />
          <Route path="/sources/:id/mapping" element={<MappingPageProbe />} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>
  );
}

describe("MappingReview legacy route", () => {
  it("redirects to the unified source mapping workflow", async () => {
    renderPage();
    expect(await screen.findByText("Source Mapping Workflow ?draft=map-1")).toBeInTheDocument();
  });
});
