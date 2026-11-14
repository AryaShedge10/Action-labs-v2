import { useQuery } from "@tanstack/react-query";
import { api } from "../services/api";

export function useEncounter(encounterId: string | undefined) {
  return useQuery({
    queryKey: ["encounter", encounterId],
    enabled: Boolean(encounterId),
    queryFn: () => api.getEncounter(encounterId!),
  });
}
