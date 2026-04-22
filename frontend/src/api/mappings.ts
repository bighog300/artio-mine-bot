import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  getMappings,
  getMapping,
  testMapping,
  updateMapping,
  type MappingDetail,
  type MappingListItem,
  type MappingTestResponse,
} from "@/lib/api";

export type { MappingListItem, MappingDetail, MappingTestResponse };

export function useMappings() {
  return useQuery({ queryKey: ["mappings"], queryFn: getMappings });
}

export function useMapping(id?: string) {
  return useQuery({
    queryKey: ["mapping", id],
    queryFn: () => getMapping(id as string),
    enabled: Boolean(id),
  });
}

export function useTestMapping() {
  return useMutation({ mutationFn: testMapping });
}

export function useUpdateMapping() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: updateMapping,
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ["mappings"] });
      queryClient.setQueryData(["mapping", data.id], data);
    },
  });
}
