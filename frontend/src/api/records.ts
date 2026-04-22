import { useQuery } from "@tanstack/react-query";
import { getRecord, getRecords, type ArtRecord, type PaginatedResponse, type RecordFilters } from "@/lib/api";

export type { ArtRecord, RecordFilters, PaginatedResponse };

export function useRecords(filters: RecordFilters) {
  return useQuery({
    queryKey: ["records", filters],
    queryFn: () => getRecords(filters),
  });
}

export function useRecord(id?: string) {
  return useQuery({
    queryKey: ["record", id],
    queryFn: () => getRecord(id as string),
    enabled: Boolean(id),
  });
}
