import { BrowserRouter, Routes, Route } from "react-router-dom";
import { Layout } from "@/components/shared/Layout";
import { Dashboard } from "@/pages/Dashboard";
import { Sources } from "@/pages/Sources";
import { SourceDetail } from "@/pages/SourceDetail";
import { Records } from "@/pages/Records";
import { RecordDetail } from "@/pages/RecordDetail";
import { Images } from "@/pages/Images";
import { Export } from "@/pages/Export";

export default function App() {
  return (
    <BrowserRouter>
      <Layout>
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/sources" element={<Sources />} />
          <Route path="/sources/:id" element={<SourceDetail />} />
          <Route path="/records" element={<Records />} />
          <Route path="/records/:id" element={<RecordDetail />} />
          <Route path="/images" element={<Images />} />
          <Route path="/export" element={<Export />} />
        </Routes>
      </Layout>
    </BrowserRouter>
  );
}
