export type SoapSection = "subjective" | "objective" | "assessment" | "plan";

export interface Patient {
  id: string;
  name: string;
  age?: number | null;
  date_of_birth?: string | null;
  sex: string;
  gender?: string | null;
  allergies: string[];
  medications: string[];
  medical_history: string[];
  family_history: string[];
  known_conditions: string[];
}

export interface TranscriptSegment {
  id: string;
  speaker: string;
  start: number;
  end: number;
  text: string;
  confidence: number;
  source_type?: string;
}

export interface SoapStatement {
  id: string;
  text: string;
  citations: string[];
  origin: "ai" | "physician";
  deleted: boolean;
}

export interface ClinicalNote {
  subjective: SoapStatement[];
  objective: SoapStatement[];
  assessment: SoapStatement[];
  plan: SoapStatement[];
}

export interface Claim {
  id: string;
  text: string;
  section: SoapSection;
  citations: string[];
  confidence: number;
  origin: "ai" | "physician";
  deleted: boolean;
}

export interface Conflict {
  id: string;
  severity: "CRITICAL" | "HIGH" | "MEDIUM" | "LOW" | string;
  category: string;
  title: string;
  message: string;
  claim_id?: string | null;
  resolved?: boolean;
}

export interface ClaimValidation {
  claim_id: string;
  text: string;
  section: string;
  citations: string[];
  evidence_ids: string[];
  status: string;
  origin: string;
  deleted: boolean;
}

export interface ValidationResult {
  summary: {
    grounding_score: number;
    citation_coverage?: number | null;
    supported_claims: number;
    unsupported_claims: number;
    contradictory_claims: number;
    uncertain_claims: number;
    total_claims: number;
    disclaimer: string;
  };
  conflicts: Conflict[];
  claims: ClaimValidation[];
  critical_conflicts: number;
  high_conflicts: number;
  review_status: string;
  banner: string;
}

export interface Encounter {
  encounter_id: string;
  physician_id: string;
  physician_name: string;
  encounter_at: string;
  ai_status: string;
  validation_status: string;
  workflow_status: string;
  reviewed: boolean;
  finalized_at: string | null;
  patient: Patient;
  transcript: { segments: TranscriptSegment[] };
  clinical_note: ClinicalNote;
  claims: Claim[];
  acknowledgements: Record<string, boolean>;
  privacy: { mode: string; label: string };
  validation: ValidationResult;
  handoffs: Array<{ status: string; summary: Record<string, unknown>; created_at: string }>;
}

export interface EncounterListItem {
  encounter_id: string;
  patient_id: string;
  encounter_at: string;
  workflow_status: string;
  ai_status: string;
  validation_status: string;
  physician_name: string;
}

export interface AuditEvent {
  time: string;
  action: string;
  detail: string;
  physician_id: string;
}

export type DoseStatus = "SUGGESTED" | "NEEDS_INFO" | "NOT_RECOMMENDED" | "NOT_SUPPORTED";

export interface DoseCitation {
  page: number;
  table_or_section: string;
  quote: string | null;
  supports: string;
}

export interface DoseSuggestion {
  status: DoseStatus;
  drug: string;
  resolved_drug: string | null;
  start_dose: number | null;
  unit: string | null;
  frequency: string | null;
  max_daily_dose: number | null;
  titration_interval: string | null;
  adjustments_applied: string[];
  warnings: string[];
  reasons: string[];
  needs_info: string[];
  citations: DoseCitation[];
  knowledge_source: string;
  reviewed_by_clinician: boolean;
  disclaimer: string;
}

export interface PrescribedDrug {
  medication: string;
  intent: string;
  dose: string | null;
  frequency: string | null;
}
