import { BrowserRouter, Routes, Route } from "react-router-dom";
import { Layout } from "@/components/shared/Layout";
import { Dashboard } from "@/pages/Dashboard";
import { Sources } from "@/pages/Sources";
import { SourceDetail } from "@/pages/SourceDetail";
import { SourceOperations } from "@/pages/SourceOperations";
import { SourceMapping } from "@/pages/SourceMapping";
import { MappingReview } from "@/pages/MappingReview";
import { MappingDrift } from "@/pages/MappingDrift";
import { Mappings } from "@/pages/Mappings";
import { MappingDetail } from "@/pages/MappingDetail";
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
import { MobileTest } from "@/pages/MobileTest";
import { Entities } from "@/pages/Entities";
import { EntityDetail } from "@/pages/EntityDetail";
import { EntityConflicts } from "@/pages/EntityConflicts";
import { EntityMergeCandidates } from "@/pages/EntityMergeCandidates";
import { EntityCompare } from "@/pages/EntityCompare";
import { SmartMining } from "@/pages/SmartMining";
import { SmartMiningProgress } from "@/pages/SmartMiningProgress";
import { ToastProvider } from "@/components/ui";
import { ApiAuthNotice } from "@/components/shared/ApiAuthNotice";

export default function App() {
  return (
    <BrowserRouter>
      <ToastProvider>
      <ApiAuthNotice />
      <Layout>
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/sources" element={<Sources />} />
          <Route path="/sources/:id" element={<SourceDetail />} />
          <Route path="/sources/:id/operations" element={<SourceOperations />} />
          <Route path="/sources/:id/mapping" element={<SourceMapping />} />
          <Route path="/sources/:id/mappings/:mappingId/review" element={<MappingReview />} />
          <Route path="/sources/:id/drift" element={<MappingDrift />} />
          <Route path="/mappings" element={<Mappings />} />
          <Route path="/mappings/:id" element={<MappingDetail />} />
          <Route path="/records" element={<Records />} />
          <Route path="/admin-review" element={<AdminReview />} />
          <Route path="/duplicates" element={<DuplicateResolution />} />
          <Route path="/semantic" element={<SemanticExplorer />} />
          <Route path="/audit" element={<AuditTrail />} />
          <Route path="/records/:id" element={<RecordDetail />} />
          <Route path="/entities" element={<Entities />} />
          <Route path="/entities/:id" element={<EntityDetail />} />
          <Route path="/entities/:id/conflicts" element={<EntityConflicts />} />
          <Route path="/entities/merge" element={<EntityMergeCandidates />} />
          <Route path="/entities/compare/:a/:b" element={<EntityCompare />} />
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
          <Route path="/smart-mine" element={<SmartMining />} />
          <Route path="/smart-mine/:sourceId/progress" element={<SmartMiningProgress />} />
          <Route path="/backfill" element={<Backfill />} />
          <Route path="/mobile-test" element={<MobileTest />} />
        </Routes>
      </Layout>
      </ToastProvider>
    </BrowserRouter>
  );
}
