import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import axios from "axios";
import { buildAuthHeaders } from "@/lib/api";

const API_URL = import.meta.env.VITE_API_URL || "/api";
const entitiesApi = axios.create({ baseURL: API_URL });

type ConflictStatus = "none" | "minor" | "major";

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
  source: string;
}

export interface EntityConflict {
  field: string;
  severity: "minor" | "major";
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
  const { data } = await entitiesApi.get<MergeCandidate[] | { items: MergeCandidate[] }>("/entities/merge-candidates", authConfig());
  return Array.isArray(data) ? data : data.items;
}

async function getEntityComparison(a: string, b: string): Promise<EntityComparison> {
  const { data } = await entitiesApi.get<EntityComparison>(`/entities/compare/${a}/${b}`, authConfig());
  return data;
}

async function mergeEntities(payload: MergeEntitiesInput): Promise<{ merged_entity_id: string }> {
  const { data } = await entitiesApi.post<{ merged_entity_id: string }>("/entities/merge", payload, authConfig());
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
