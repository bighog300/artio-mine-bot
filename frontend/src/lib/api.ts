import axios from "axios";

const BASE_URL = import.meta.env.VITE_API_URL ?? "http://localhost:8000";

const api = axios.create({ baseURL: BASE_URL });

// ─── Types ────────────────────────────────────────────────────────────────────

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  skip: number;
  limit: number;
}

export interface SourceStats {
  pending_records: number;
  approved_records: number;
  rejected_records: number;
  high_confidence: number;
  medium_confidence: number;
  low_confidence: number;
}

export interface Source {
  id: string;
  url: string;
  name: string | null;
  status: string;
  total_pages: number;
  total_records: number;
  last_crawled_at: string | null;
  created_at: string;
  site_map?: string | null;
  stats?: SourceStats;
}

export interface CreateSourceInput {
  url: string;
  name?: string;
}

export interface MineOptions {
  max_depth?: number;
  max_pages?: number;
  sections?: string[];
}

export interface Job {
  id: string;
  source_id: string;
  job_type: string;
  status: string;
  message?: string;
}

export interface MiningStatus {
  source_id: string;
  status: string;
  current_job?: {
    id: string;
    job_type: string;
    status: string;
    started_at: string | null;
  } | null;
  progress?: {
    pages_crawled: number;
    pages_total_estimated: number;
    records_extracted: number;
    percent_complete: number;
  } | null;
}

export interface SiteMap {
  root_url: string;
  platform: string;
  sections: Array<{
    name: string;
    url: string;
    content_type: string;
    pagination_type: string;
    index_pattern: string | null;
    confidence: number;
  }>;
}

export interface Page {
  id: string;
  source_id: string;
  url: string;
  page_type: string;
  status: string;
  title: string | null;
  depth: number;
  fetch_method: string | null;
  crawled_at: string | null;
  record_count: number;
}

export interface PageFilters {
  source_id?: string;
  status?: string;
  page_type?: string;
  skip?: number;
  limit?: number;
}

export interface ImageRecord {
  id: string;
  url: string;
  image_type: string;
  alt_text: string | null;
  confidence: number;
  is_valid: boolean;
  mime_type?: string | null;
  width?: number | null;
  height?: number | null;
}

export interface ArtRecord {
  id: string;
  source_id: string;
  record_type: string;
  status: string;
  title: string | null;
  description: string | null;
  confidence_score: number;
  confidence_band: string;
  confidence_reasons: string[];
  source_url: string | null;
  image_count?: number;
  primary_image_url?: string | null;
  created_at: string;
  // Event/Exhibition
  start_date?: string | null;
  end_date?: string | null;
  venue_name?: string | null;
  venue_address?: string | null;
  artist_names?: string[];
  ticket_url?: string | null;
  is_free?: boolean | null;
  price_text?: string | null;
  curator?: string | null;
  // Artist
  bio?: string | null;
  nationality?: string | null;
  birth_year?: number | null;
  website_url?: string | null;
  instagram_url?: string | null;
  email?: string | null;
  avatar_url?: string | null;
  mediums?: string[];
  collections?: string[];
  // Venue
  address?: string | null;
  city?: string | null;
  country?: string | null;
  phone?: string | null;
  opening_hours?: string | null;
  // Artwork
  medium?: string | null;
  year?: number | null;
  dimensions?: string | null;
  price?: string | null;
  // Admin
  admin_notes?: string | null;
  // Images (detail)
  images?: ImageRecord[];
  primary_image_id?: string | null;
}

export interface RecordFilters {
  source_id?: string;
  record_type?: string;
  status?: string;
  confidence_band?: string;
  search?: string;
  skip?: number;
  limit?: number;
}

export interface BulkApproveParams {
  source_id: string;
  min_confidence?: number;
  record_type?: string;
}

export interface ImageFilters {
  record_id?: string;
  source_id?: string;
  image_type?: string;
  is_valid?: boolean;
  skip?: number;
  limit?: number;
}

export interface ValidationResult {
  url: string;
  is_valid: boolean;
  mime_type?: string | null;
  status_code?: number | null;
  error?: string | null;
}

export interface ExportPreview {
  record_count: number;
  by_type: {
    artist: number;
    event: number;
    exhibition: number;
    venue: number;
    artwork: number;
  };
  artio_configured: boolean;
}

export interface ExportParams {
  source_id?: string;
  record_ids?: string[];
}

export interface ExportResult {
  exported_count: number;
  failed_count: number;
  errors: string[];
}

export interface GlobalStats {
  sources: { total: number; active: number; done: number };
  records: {
    total: number;
    pending: number;
    approved: number;
    rejected: number;
    exported: number;
    by_type: Record<string, number>;
    by_confidence: Record<string, number>;
  };
  pages: { total: number; crawled: number; error: number };
}

// ─── API Functions ────────────────────────────────────────────────────────────

// Sources
export const getSources = (): Promise<PaginatedResponse<Source>> =>
  api.get("/api/sources").then((r) => r.data);

export const getSource = (id: string): Promise<Source> =>
  api.get(`/api/sources/${id}`).then((r) => r.data);

export const createSource = (data: CreateSourceInput): Promise<Source> =>
  api.post("/api/sources", data).then((r) => r.data);

export const deleteSource = (id: string): Promise<void> =>
  api.delete(`/api/sources/${id}`).then(() => undefined);

// Mining
export const startMining = (sourceId: string, opts?: MineOptions): Promise<Job> =>
  api.post(`/api/mine/${sourceId}/start`, opts ?? {}).then((r) => r.data);

export const getMiningStatus = (sourceId: string): Promise<MiningStatus> =>
  api.get(`/api/mine/${sourceId}/status`).then((r) => r.data);

export const mapSite = (sourceId: string): Promise<SiteMap> =>
  api.post(`/api/mine/${sourceId}/map`).then((r) => r.data.site_map);

export const pauseMining = (sourceId: string): Promise<void> =>
  api.post(`/api/mine/${sourceId}/pause`).then(() => undefined);

export const resumeMining = (sourceId: string): Promise<void> =>
  api.post(`/api/mine/${sourceId}/resume`).then(() => undefined);

// Pages
export const getPages = (params: PageFilters): Promise<PaginatedResponse<Page>> =>
  api.get("/api/pages", { params }).then((r) => r.data);

export const getPage = (id: string): Promise<Page> =>
  api.get(`/api/pages/${id}`).then((r) => r.data);

export const reclassifyPage = (id: string): Promise<Page> =>
  api.post(`/api/pages/${id}/reclassify`).then((r) => r.data);

export const reextractPage = (id: string): Promise<ArtRecord> =>
  api.post(`/api/pages/${id}/reextract`).then((r) => r.data);

// Records
export const getRecords = (params: RecordFilters): Promise<PaginatedResponse<ArtRecord>> =>
  api.get("/api/records", { params }).then((r) => r.data);

export const getRecord = (id: string): Promise<ArtRecord> =>
  api.get(`/api/records/${id}`).then((r) => r.data);

export const updateRecord = (id: string, data: Partial<ArtRecord>): Promise<ArtRecord> =>
  api.patch(`/api/records/${id}`, data).then((r) => r.data);

export const approveRecord = (id: string): Promise<ArtRecord> =>
  api.post(`/api/records/${id}/approve`).then((r) => r.data);

export const rejectRecord = (id: string, reason?: string): Promise<ArtRecord> =>
  api.post(`/api/records/${id}/reject`, { reason }).then((r) => r.data);

export const bulkApprove = (params: BulkApproveParams): Promise<{ approved_count: number }> =>
  api.post("/api/records/bulk-approve", params).then((r) => r.data);

export const setPrimaryImage = (recordId: string, imageId: string): Promise<ArtRecord> =>
  api.post(`/api/records/${recordId}/set-primary-image`, { image_id: imageId }).then((r) => r.data);

// Images
export const getImages = (params: ImageFilters): Promise<PaginatedResponse<ImageRecord>> =>
  api.get("/api/images", { params }).then((r) => r.data);

export const validateImages = (urls: string[]): Promise<ValidationResult[]> =>
  api.post("/api/images/validate", { urls }).then((r) => r.data.results);

// Export
export const getExportPreview = (sourceId?: string): Promise<ExportPreview> =>
  api.get("/api/export/preview", { params: sourceId ? { source_id: sourceId } : {} }).then((r) => r.data);

export const pushToArtio = (params: ExportParams): Promise<ExportResult> =>
  api.post("/api/export/push", params).then((r) => r.data);

// Stats
export const getStats = (): Promise<GlobalStats> =>
  api.get("/api/stats").then((r) => r.data);
