import type {
  AuditEvent,
  DoseSuggestion,
  Encounter,
  EncounterListItem,
  PrescribedDrug,
} from "../types/clinical";

const API = import.meta.env.VITE_API_URL ?? "";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...(init?.headers ?? {}),
    },
  });
  if (!response.ok) {
    let detail = "Request failed.";
    try {
      const body = await response.json();
      detail = body.detail || detail;
    } catch {
      /* ignore */
    }
    throw new Error(detail);
  }
  return response.json() as Promise<T>;
}

export const api = {
  health: () => request<{ status: string }>("/api/health"),
  listEncounters: () => request<EncounterListItem[]>("/api/encounters"),
  getEncounter: (id: string) => request<Encounter>(`/api/encounters/${id}`),
  loadDemo: () => request<Encounter>("/api/demo/load", { method: "POST" }),
  saveNote: (id: string, body: unknown) =>
    request<Encounter>(`/api/encounters/${id}/note`, {
      method: "PATCH",
      body: JSON.stringify(body),
    }),
  validate: (id: string) =>
    request(`/api/encounters/${id}/validate`, { method: "POST" }),
  finalize: (id: string, body: unknown) =>
    request<Encounter>(`/api/encounters/${id}/finalize`, {
      method: "POST",
      body: JSON.stringify(body),
    }),
  prescribedDrugs: (id: string) => request<PrescribedDrug[]>(`/api/encounters/${id}/prescribed-drugs`),
  doseSuggestion: (id: string, drug: string, patient?: Record<string, unknown>) =>
    request<DoseSuggestion>(`/api/encounters/${id}/dose-suggestion`, {
      method: "POST",
      body: JSON.stringify({ drug, patient }),
    }),
  doseDecision: (id: string, body: unknown) =>
    request<{ recorded: boolean; action: string }>(`/api/encounters/${id}/dose-decision`, {
      method: "POST",
      body: JSON.stringify(body),
    }),
  audit: (id: string) => request<AuditEvent[]>(`/api/encounters/${id}/audit`),
  fhir: (id: string) => request<Record<string, unknown>>(`/api/encounters/${id}/export/fhir`),
  handoff: (id: string) =>
    request(`/api/ehr/handoff`, {
      method: "POST",
      body: JSON.stringify({ encounter_id: id }),
    }),
  pdfUrl: (id: string) => `${API}/api/encounters/${id}/export/pdf`,

  uploadAudio: async (
    file: Blob | File,
    encounterId?: string,
    patientId?: string,
    patientName?: string
  ): Promise<Encounter> => {
    const formData = new FormData();
    formData.append("file", file, file instanceof File ? file.name : "recording.webm");
    if (encounterId) formData.append("encounter_id", encounterId);
    if (patientId) formData.append("patient_id", patientId);
    if (patientName) formData.append("patient_name", patientName);

    const response = await fetch(`${API}/api/encounters/pipeline/from-audio`, {
      method: "POST",
      body: formData,
    });
    if (!response.ok) {
      let detail = "Audio pipeline failed.";
      try {
        const body = await response.json();
        detail = body.detail || detail;
      } catch {
        /* ignore */
      }
      throw new Error(detail);
    }
    return response.json() as Promise<Encounter>;
  },

  processTranscript: (
    payload: Record<string, unknown>,
    patientId?: string,
    patientName?: string
  ) =>
    request<Encounter>("/api/encounters/pipeline/from-transcript", {
      method: "POST",
      body: JSON.stringify({ ...payload, patient_id: patientId, patient_name: patientName }),
    }),
};
