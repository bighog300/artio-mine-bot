import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import axios from "axios";
import { buildAuthHeaders } from "@/lib/api";

const API_URL = import.meta.env.VITE_API_URL || "/api";
const entitiesApi = axios.create({ baseURL: API_URL });

type ConflictStatus = "none" | "minor" | "medium" | "major";

export interface EntityListItem {
  id: string;
  name: string;
  type: string;
  source_count: number;
  conflict_status: ConflictStatus;
  confidence_score: number;
  last_updated: string;
}

export interface CanonicalField {
  field: string;
  value: string;
  confidence: number;
  source?: string;
  sources?: Array<{ source: string; confidence?: number }>;
}

export interface EntityConflict {
  field: string;
  severity: "minor" | "medium" | "major";
  explanation: string;
  impact_count?: number;
  canonical_value?: string;
  options?: Array<{ source: string; value: string; confidence: number }>;
}

export interface SourceVariant {
  source_name: string;
  source_id?: string;
  confidence: number;
  values: Record<string, string>;
}

export interface EntityRelationship {
  id: string;
  name: string;
  type: string;
  relationship_type: string;
  count?: number;
  confidence?: number;
  importance?: number;
  last_updated?: string;
}

export interface EntityDetail {
  id: string;
  name: string;
  type: string;
  confidence_score: number;
  source_count: number;
  last_merged?: string | null;
  last_updated: string;
  canonical_fields: CanonicalField[];
  conflicts: EntityConflict[];
  source_variants: SourceVariant[];
  relationships: EntityRelationship[];
}

export interface EntityConflictResponse {
  entity_id: string;
  conflicts: EntityConflict[];
}

export interface MergeCandidate {
  id: string;
  entity_a: { id: string; name: string; type: string };
  entity_b: { id: string; name: string; type: string };
  similarity_score: number;
  matching_signals: string[];
  signal_breakdown?: {
    name_similarity?: number;
    shared_relationships?: boolean;
    overlapping_fields?: string[];
    conflicting_fields?: string[];
  };
}

export interface EntityComparison {
  entity_a: { id: string; name: string; type: string; fields: Record<string, string> };
  entity_b: { id: string; name: string; type: string; fields: Record<string, string> };
  preview: {
    resulting_fields: Record<string, string>;
    combined_relationships: Array<{ type: string; count: number }>;
  };
}

export interface ResolveConflictInput {
  entityId: string;
  field: string;
  resolution_type: "source" | "manual" | "keep_canonical";
  value?: string;
  source?: string;
}

export interface MergeEntitiesInput {
  primary_entity_id: string;
  secondary_entity_id: string;
  field_choices?: Record<string, "a" | "b">;
}

export interface EntityDecisionHistoryItem {
  id: string;
  action_type: "resolve" | "merge" | "split";
  field?: string;
  old_value?: string | null;
  new_value?: string | null;
  source?: string | null;
  operator?: string | null;
  timestamp: string;
}

export interface UndoMergeImpact {
  restored_entities: number;
  relinked_records: number;
}

export interface UndoMergeSupport {
  supported: boolean;
  impact?: UndoMergeImpact;
}

function authConfig() {
  return { headers: buildAuthHeaders() };
}

async function getEntities(filters: { type?: string; conflict_status?: string } = {}): Promise<EntityListItem[]> {
  const { data } = await entitiesApi.get<EntityListItem[] | { items: EntityListItem[] }>("/entities", {
    ...authConfig(),
    params: filters,
  });
  return Array.isArray(data) ? data : data.items;
}

async function getEntity(id: string): Promise<EntityDetail> {
  const { data } = await entitiesApi.get<EntityDetail>(`/entities/${id}`, authConfig());
  return data;
}

async function getEntityConflicts(id: string): Promise<EntityConflictResponse> {
  const { data } = await entitiesApi.get<EntityConflictResponse>(`/entities/${id}/conflicts`, authConfig());
  return data;
}

async function resolveConflict(input: ResolveConflictInput): Promise<{ status: string }> {
  const { entityId, ...payload } = input;
  const { data } = await entitiesApi.post<{ status: string }>(`/entities/${entityId}/resolve`, payload, authConfig());
  return data;
}

async function getMergeCandidates(): Promise<MergeCandidate[]> {
  const { data } = await entitiesApi.get<{ items: Array<{
    left_id: string;
    right_id: string;
    left_name: string | null;
    right_name: string | null;
    similarity_score: number;
    strong_signals?: string[];
  }> }>("/suggest/duplicates", { ...authConfig(), params: { auto_merge: false } });
  return (data.items ?? []).map((item) => ({
    id: `${item.left_id}:${item.right_id}`,
    entity_a: { id: item.left_id, name: item.left_name ?? "Unknown", type: "artist" },
    entity_b: { id: item.right_id, name: item.right_name ?? "Unknown", type: "artist" },
    similarity_score: item.similarity_score,
    matching_signals: item.strong_signals ?? [],
  }));
}

async function getEntityComparison(a: string, b: string): Promise<EntityComparison> {
  const { data } = await entitiesApi.get<EntityComparison>(`/entities/compare/${a}/${b}`, authConfig());
  return data;
}

async function mergeEntities(payload: MergeEntitiesInput): Promise<{ merged_entity_id: string }> {
  const { data } = await entitiesApi.post<{ merged_entity_id: string }>("/entities/merge", payload, authConfig());
  return data;
}

async function getEntityHistory(id: string): Promise<EntityDecisionHistoryItem[]> {
  const { data } = await entitiesApi.get<EntityDecisionHistoryItem[] | { items: EntityDecisionHistoryItem[] }>(`/entities/${id}/history`, authConfig());
  const items = Array.isArray(data) ? data : data.items;
  return items.sort((a, b) => new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime());
}

async function getUndoMergeSupport(id: string): Promise<UndoMergeSupport> {
  try {
    const { data } = await entitiesApi.get<UndoMergeSupport>(`/entities/${id}/undo-merge`, authConfig());
    return data;
  } catch (error) {
    if (axios.isAxiosError(error) && error.response?.status === 404) {
      return { supported: false };
    }
    throw error;
  }
}

async function undoMerge(id: string): Promise<{ status: string }> {
  const { data } = await entitiesApi.post<{ status: string }>(`/entities/${id}/undo-merge`, undefined, authConfig());
  return data;
}

export function useEntities(filters: { type?: string; conflict_status?: string }) {
  return useQuery({ queryKey: ["entities", filters], queryFn: () => getEntities(filters) });
}

export function useEntity(id?: string) {
  return useQuery({ queryKey: ["entity", id], queryFn: () => getEntity(id as string), enabled: Boolean(id) });
}

export function useEntityConflicts(id?: string) {
  return useQuery({ queryKey: ["entity-conflicts", id], queryFn: () => getEntityConflicts(id as string), enabled: Boolean(id) });
}

export function useResolveConflict() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: resolveConflict,
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: ["entity", variables.entityId] });
      queryClient.invalidateQueries({ queryKey: ["entity-conflicts", variables.entityId] });
      queryClient.invalidateQueries({ queryKey: ["entities"] });
    },
  });
}

export function useMergeCandidates() {
  return useQuery({ queryKey: ["merge-candidates"], queryFn: getMergeCandidates });
}

export function useEntityComparison(a?: string, b?: string) {
  return useQuery({ queryKey: ["entity-compare", a, b], queryFn: () => getEntityComparison(a as string, b as string), enabled: Boolean(a && b) });
}

export function useMergeEntities() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: mergeEntities,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["entities"] });
      queryClient.invalidateQueries({ queryKey: ["merge-candidates"] });
    },
  });
}

export function useEntityHistory(id?: string) {
  return useQuery({ queryKey: ["entity-history", id], queryFn: () => getEntityHistory(id as string), enabled: Boolean(id) });
}

export function useUndoMergeSupport(id?: string) {
  return useQuery({ queryKey: ["undo-merge-support", id], queryFn: () => getUndoMergeSupport(id as string), enabled: Boolean(id) });
}

export function useUndoMerge() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: undoMerge,
    onSuccess: (_, entityId) => {
      queryClient.invalidateQueries({ queryKey: ["entity", entityId] });
      queryClient.invalidateQueries({ queryKey: ["entity-history", entityId] });
      queryClient.invalidateQueries({ queryKey: ["entities"] });
      queryClient.invalidateQueries({ queryKey: ["merge-candidates"] });
    },
  });
}
