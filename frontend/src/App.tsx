import { BrowserRouter, Routes, Route } from "react-router-dom";
import { Layout } from "@/components/shared/Layout";
import { Dashboard } from "@/pages/Dashboard";
import { Sources } from "@/pages/Sources";
import { SourceDetail } from "@/pages/SourceDetail";
import { SourceMapping } from "@/pages/SourceMapping";
import { Records } from "@/pages/Records";
import { RecordDetail } from "@/pages/RecordDetail";
import { Pages } from "@/pages/Pages";
import { Images } from "@/pages/Images";
import { Export } from "@/pages/Export";
import { Settings } from "@/pages/Settings";
import { Logs } from "@/pages/Logs";
import { AdminReview } from "@/pages/AdminReview";
import { DuplicateResolution } from "@/pages/DuplicateResolution";
import { SemanticExplorer } from "@/pages/SemanticExplorer";
import { AuditTrail } from "@/pages/AuditTrail";
import { ApiAccess } from "@/pages/ApiAccess";
import { Jobs } from "@/pages/Jobs";
import { Queues } from "@/pages/Queues";
import { Backfill } from "@/pages/Backfill";
import { JobDetail } from "@/pages/JobDetail";
import { Workers } from "@/pages/Workers";

export default function App() {
  return (
    <BrowserRouter>
      <Layout>
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/sources" element={<Sources />} />
          <Route path="/sources/:id" element={<SourceDetail />} />
          <Route path="/sources/:id/mapping" element={<SourceMapping />} />
          <Route path="/records" element={<Records />} />
          <Route path="/admin-review" element={<AdminReview />} />
          <Route path="/duplicates" element={<DuplicateResolution />} />
          <Route path="/semantic" element={<SemanticExplorer />} />
          <Route path="/audit" element={<AuditTrail />} />
          <Route path="/records/:id" element={<RecordDetail />} />
          <Route path="/pages" element={<Pages />} />
          <Route path="/jobs" element={<Jobs />} />
          <Route path="/jobs/:id" element={<JobDetail />} />
          <Route path="/queues" element={<Queues />} />
          <Route path="/workers" element={<Workers />} />
          <Route path="/images" element={<Images />} />
          <Route path="/export" element={<Export />} />
          <Route path="/logs" element={<Logs />} />
          <Route path="/settings" element={<Settings />} />
          <Route path="/api-access" element={<ApiAccess />} />
          <Route path="/backfill" element={<Backfill />} />
        </Routes>
      </Layout>
    </BrowserRouter>
  );
}
