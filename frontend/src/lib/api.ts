import axios from "axios";

const API_URL = import.meta.env.VITE_API_URL || "/api";

const api = axios.create({ baseURL: API_URL });
api.interceptors.response.use(
  (response) => response,
  (error) => {
    const detail = error?.response?.data?.detail;
    if (typeof detail === "string" && detail.length > 0) {
      return Promise.reject(new Error(detail));
    }
    return Promise.reject(error);
  }
);

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
  operational_status?: string;
  total_pages: number;
  total_records: number;
  last_crawled_at: string | null;
  created_at: string;
  error_message?: string | null;
  site_map?: string | null;
  crawl_intent?: string;
  max_depth?: number | null;
  max_pages?: number | null;
  enabled?: boolean;
  queue_paused?: boolean;
  crawl_hints?: Record<string, unknown> | null;
  extraction_rules?: Record<string, unknown> | null;
  stats?: SourceStats;
}

export interface CreateSourceInput {
  url: string;
  name?: string;
  crawl_intent?: "site_root" | "directory_listing" | "detail_entity" | "test_crawl";
  max_pages?: number;
  max_depth?: number;
  enabled?: boolean;
  crawl_hints?: Record<string, unknown>;
  extraction_rules?: Record<string, unknown>;
}

export interface UpdateSourceInput extends Partial<CreateSourceInput> {
  status?: string;
  operational_status?: string;
  queue_paused?: boolean;
}

export interface MineOptions {
  max_depth?: number;
  max_pages?: number;
  sections?: string[];
}

export interface MineStartResponse {
  job_id: string;
  source_id: string;
  status: string;
  message: string;
}

export interface Job {
  id: string;
  source_id: string;
  job_type: string;
  status: string;
  message?: string;
  attempts?: number;
  started_at?: string | null;
  completed_at?: string | null;
  error_message?: string | null;
  source?: string | null;
  processed_count?: number;
  failure_count?: number;
  duration_seconds?: number | null;
}

export interface QueueState {
  name: string;
  pending: number;
  running: number;
  failed: number;
  paused: number;
  oldest_item_age_seconds: number;
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
    pages_eligible_for_extraction: number;
    pages_classified: number;
    pages_skipped: number;
    pages_error: number;
    records_extracted: number;
    records_by_type: Record<string, number>;
    images_collected: number;
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

export interface LogEntry {
  id: string;
  timestamp: string;
  level: "debug" | "info" | "warning" | "error";
  service: "api" | "worker";
  source_id: string | null;
  message: string;
  context: string | null;
}

export interface LogFilters {
  level?: string;
  service?: string;
  source_id?: string;
  search?: string;
  date_from?: string;
  date_to?: string;
  skip?: number;
  limit?: number;
}

export interface AdjacentRecordResponse {
  prev_id: string | null;
  next_id: string | null;
}

export interface ReviewArtistSummary {
  id: string;
  source_id: string;
  title: string;
  completeness_score: number;
  missing_fields: string[];
  has_conflicts: boolean;
  conflict_fields: string[];
}

export interface ReviewArtistDetail {
  id: string;
  source_id: string;
  title: string;
  canonical_fields: Record<string, unknown>;
  completeness_score: number;
  missing_fields: string[];
  provenance: Record<string, unknown>;
  conflicts: Record<string, Array<{ value: string; selected?: boolean; resolved?: boolean }>>;
  related: Record<string, Array<{ id: string; title: string; source_url?: string; status?: string }>>;
}

export interface DuplicateCandidate {
  id: string;
  left_id: string;
  right_id: string;
  left_name: string | null;
  right_name: string | null;
  similarity_score: number;
  reason: string;
  status: string;
  reviewed_by: string | null;
}

export interface AuditAction {
  id: string;
  action_type: string;
  user: string | null;
  source_id: string | null;
  record_id: string | null;
  affected_records: string[];
  details: Record<string, unknown>;
  timestamp: string;
}

export interface ApiKeyItem {
  id: string;
  tenant_id: string;
  name: string;
  key_prefix: string;
  enabled: boolean;
  usage_count: number;
  created_at: string;
  last_used_at: string | null;
}

export interface ApiKeyCreateInput {
  name: string;
  tenant_id?: string;
  permissions?: string[];
}

export interface ApiUsageSummary {
  total_requests: number;
  avg_response_time_ms: number;
  endpoint_usage: Array<{ endpoint: string; count: number }>;
}

// ─── API Functions ────────────────────────────────────────────────────────────

// Sources
export const getSources = (): Promise<PaginatedResponse<Source>> =>
  api.get("/sources").then((r) => r.data);

export const getSource = (id: string): Promise<Source> =>
  api.get(`/sources/${id}`).then((r) => r.data);

export const getSourceJobs = (sourceId: string): Promise<{ items: Job[] }> =>
  api.get(`/sources/${sourceId}/jobs`).then((r) => r.data);

export const createSource = (data: CreateSourceInput): Promise<Source> =>
  api.post("/sources", data).then((r) => r.data);

export const updateSource = (id: string, data: UpdateSourceInput): Promise<Source> =>
  api.patch(`/sources/${id}`, data).then((r) => r.data);

export const deleteSource = (id: string): Promise<void> =>
  api.delete(`/sources/${id}`).then(() => undefined);

export const startDiscovery = (sourceId: string): Promise<{ source_id: string; status: string }> =>
  api.post(`/sources/${sourceId}/actions/start-discovery`).then((r) => r.data);

export const startFullMining = (sourceId: string): Promise<{ source_id: string; status: string }> =>
  api.post(`/sources/${sourceId}/actions/start-full-mining`).then((r) => r.data);

export const pauseSource = (sourceId: string): Promise<{ source_id: string; status: string }> =>
  api.post(`/sources/${sourceId}/actions/pause`).then((r) => r.data);

export const resumeSource = (sourceId: string): Promise<{ source_id: string; status: string }> =>
  api.post(`/sources/${sourceId}/actions/resume`).then((r) => r.data);

export const stopSource = (sourceId: string): Promise<{ source_id: string; status: string }> =>
  api.post(`/sources/${sourceId}/actions/stop`).then((r) => r.data);

export const retryFailedSource = (sourceId: string): Promise<{ source_id: string; status: string }> =>
  api.post(`/sources/${sourceId}/actions/retry-failed`).then((r) => r.data);

// Mining
export const startMining = (sourceId: string, opts?: MineOptions): Promise<MineStartResponse> =>
  api.post(`/mine/${sourceId}/start`, opts ?? {}).then((r) => r.data);

export const getMiningStatus = (sourceId: string): Promise<MiningStatus> =>
  api.get(`/mine/${sourceId}/status`).then((r) => r.data);

export const mapSite = (sourceId: string): Promise<SiteMap> =>
  api.post(`/mine/${sourceId}/map`).then((r) => r.data.site_map);

export const pauseMining = (sourceId: string): Promise<void> =>
  api.post(`/mine/${sourceId}/pause`).then(() => undefined);

export const resumeMining = (sourceId: string): Promise<void> =>
  api.post(`/mine/${sourceId}/resume`).then(() => undefined);

// Pages
export const getPages = (params: PageFilters): Promise<PaginatedResponse<Page>> =>
  api.get("/pages", { params }).then((r) => r.data);

export const getPage = (id: string): Promise<Page> =>
  api.get(`/pages/${id}`).then((r) => r.data);

export const reclassifyPage = (id: string): Promise<Page> =>
  api.post(`/pages/${id}/reclassify`).then((r) => r.data);

export const reextractPage = (id: string): Promise<ArtRecord> =>
  api.post(`/pages/${id}/reextract`).then((r) => r.data);

// Records
export const getRecords = (params: RecordFilters): Promise<PaginatedResponse<ArtRecord>> =>
  api.get("/records", { params }).then((r) => r.data);

export const getRecord = (id: string): Promise<ArtRecord> =>
  api.get(`/records/${id}`).then((r) => r.data);

export const getAdjacentRecords = (
  id: string,
  params?: { source_id?: string; status?: string }
): Promise<AdjacentRecordResponse> =>
  api.get(`/records/${id}/adjacent`, { params }).then((r) => r.data);

export const updateRecord = (id: string, data: Partial<ArtRecord>): Promise<ArtRecord> =>
  api.patch(`/records/${id}`, data).then((r) => r.data);

export const approveRecord = (id: string): Promise<ArtRecord> =>
  api.post(`/records/${id}/approve`).then((r) => r.data);

export const rejectRecord = (id: string, reason?: string): Promise<ArtRecord> =>
  api.post(`/records/${id}/reject`, { reason }).then((r) => r.data);

export const bulkApprove = (params: BulkApproveParams): Promise<{ approved_count: number }> =>
  api.post("/records/bulk-approve", params).then((r) => r.data);

export const setPrimaryImage = (recordId: string, imageId: string): Promise<ArtRecord> =>
  api.post(`/records/${recordId}/set-primary-image`, { image_id: imageId }).then((r) => r.data);

// Images
export const getImages = (params: ImageFilters): Promise<PaginatedResponse<ImageRecord>> =>
  api.get("/images", { params }).then((r) => r.data);

export const validateImages = (urls: string[]): Promise<ValidationResult[]> =>
  api.post("/images/validate", { urls }).then((r) => r.data.results);

// Export
export const getExportPreview = (sourceId?: string): Promise<ExportPreview> =>
  api.get("/export/preview", { params: sourceId ? { source_id: sourceId } : {} }).then((r) => r.data);

export const pushToArtio = (params: ExportParams): Promise<ExportResult> =>
  api.post("/export/push", params).then((r) => r.data);

// Stats
export const getStats = (): Promise<GlobalStats> =>
  api.get("/stats").then((r) => r.data);

// Logs
export const getLogs = (params: LogFilters): Promise<PaginatedResponse<LogEntry>> =>
  api.get("/logs", { params }).then((r) => r.data);

export const getActivityFeed = (params?: {
  source_id?: string;
  limit?: number;
}): Promise<{ items: LogEntry[] }> =>
  api.get("/logs/activity", { params }).then((r) => r.data);

export const getJobs = (params?: {
  source_id?: string;
  status?: string;
  skip?: number;
  limit?: number;
}): Promise<PaginatedResponse<Job>> => api.get("/jobs", { params }).then((r) => r.data);

export const retryJob = (jobId: string): Promise<{ id: string; status: string }> =>
  api.post(`/jobs/${jobId}/retry`).then((r) => r.data);

export const cancelJob = (jobId: string): Promise<{ id: string; status: string }> =>
  api.post(`/jobs/${jobId}/cancel`).then((r) => r.data);

export const pauseJob = (jobId: string): Promise<{ id: string; status: string }> =>
  api.post(`/jobs/${jobId}/pause`).then((r) => r.data);

export const resumeJob = (jobId: string): Promise<{ id: string; status: string }> =>
  api.post(`/jobs/${jobId}/resume`).then((r) => r.data);

export const getQueues = (): Promise<{ items: QueueState[]; total: number }> =>
  api.get("/queues").then((r) => r.data);

export const pauseQueue = (name: string): Promise<{ name: string; status: string }> =>
  api.post(`/queues/${name}/pause`).then((r) => r.data);

export const resumeQueue = (name: string): Promise<{ name: string; status: string }> =>
  api.post(`/queues/${name}/resume`).then((r) => r.data);

export const deleteLogs = (
  olderThanDays: number,
  level?: string
): Promise<{ deleted_count: number }> =>
  api
    .delete("/logs", {
      params: { older_than_days: olderThanDays, level: level || undefined },
    })
    .then((r) => r.data);

// ─── Settings types ───────────────────────────────────────────────────────────

export interface AppSettings {
  artio_api_url: string | null;
  artio_api_key_masked: string | null;
  openai_api_key_masked: string | null;
  max_crawl_depth: number;
  max_pages_per_source: number;
  crawl_delay_ms: number;
  artio_configured: boolean;
  openai_configured: boolean;
  readonly: boolean;
}

export interface SaveSettingsInput {
  artio_api_url?: string | null;
  artio_api_key?: string | null;
  openai_api_key?: string | null;
  max_crawl_depth?: number;
  max_pages_per_source?: number;
  crawl_delay_ms?: number;
}

export interface TestConnectionResult {
  success: boolean;
  message: string;
}

// Settings
export const getSettings = (): Promise<AppSettings> =>
  api.get("/settings").then((r) => r.data);

export const saveSettings = (data: SaveSettingsInput): Promise<AppSettings> =>
  api.post("/settings", data).then((r) => r.data);

export const testArtioConnection = (): Promise<TestConnectionResult> =>
  api.post("/settings/test-artio").then((r) => r.data);

// Review workflows
export const searchReviewArtists = (params?: {
  source_id?: string;
  has_conflicts?: boolean;
  completeness_lt?: number;
}): Promise<{ items: ReviewArtistSummary[]; total: number }> =>
  api.get("/review/artists", { params }).then((r) => r.data);

export const getReviewArtist = (artistId: string): Promise<ReviewArtistDetail> =>
  api.get(`/review/artists/${artistId}`).then((r) => r.data);

export const resolveReviewConflict = (
  artistId: string,
  field: string,
  selectedValue: string
): Promise<{ status: string }> =>
  api.post(`/review/artists/${artistId}/resolve`, { field, selected_value: selectedValue }).then((r) => r.data);

export const rerunReviewArtist = (artistId: string): Promise<{ result: Record<string, unknown> }> =>
  api.post(`/review/artists/${artistId}/rerun`).then((r) => r.data);

// Semantic / duplicate
export const semanticArtistSearch = (
  q: string
): Promise<{ items: Array<{ id: string; name: string; semantic_score: number; completeness_score: number }>; total: number }> =>
  api.get("/semantic/artists", { params: { q } }).then((r) => r.data);

export const relatedArtists = (
  artistId: string
): Promise<{ items: Array<{ id: string; name: string; score: number }> }> =>
  api.get(`/related/artists/${artistId}`).then((r) => r.data);

export const getDuplicateReviews = (
  status?: string
): Promise<{ items: DuplicateCandidate[]; total: number }> =>
  api.get("/duplicates/reviews", { params: { status } }).then((r) => r.data);

export const decideDuplicate = (payload: {
  left_id: string;
  right_id: string;
  decision: "merge" | "ignore" | "not_duplicate" | "reviewed";
  primary_id?: string;
  reviewer?: string;
}): Promise<{ status: string }> => api.post("/duplicates/decision", payload).then((r) => r.data);

// Metrics + audit
export const getOperationalMetrics = (): Promise<{
  total_artists: number;
  avg_completeness: number;
  conflicts_count: number;
  duplicates_detected: number;
  merges_performed: number;
  pages_processed: number;
}> => api.get("/metrics").then((r) => r.data);

export const getAuditActions = (params?: {
  action_type?: string;
  source_id?: string;
  record_id?: string;
}): Promise<PaginatedResponse<AuditAction>> =>
  api.get("/audit", { params }).then((r) => r.data);

export const createApiKey = (
  data: ApiKeyCreateInput
): Promise<{ id: string; raw_key: string; masked_key: string }> =>
  api.post("/keys", data).then((r) => r.data);

export const getApiKeys = (
  tenantId?: string
): Promise<{ items: ApiKeyItem[]; total: number }> =>
  api.get("/keys", { params: { tenant_id: tenantId || undefined } }).then((r) => r.data);

export const deleteApiKey = (keyId: string, tenantId?: string): Promise<void> =>
  api.delete(`/keys/${keyId}`, { headers: tenantId ? { "X-Tenant-ID": tenantId } : {} }).then(() => undefined);

export const getApiUsage = (tenantId?: string): Promise<ApiUsageSummary> =>
  api.get("/usage", { params: { tenant_id: tenantId || undefined } }).then((r) => r.data);
