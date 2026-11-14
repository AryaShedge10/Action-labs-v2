import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { motion } from "framer-motion";
import { AlertCircle, ArrowLeft } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { toast } from "sonner";
import ActionBar from "../components/layout/ActionBar";
import AuditDrawer from "../components/audit/AuditDrawer";
import FinalizeDialog from "../components/finalize/FinalizeDialog";
import HeaderBar from "../components/layout/HeaderBar";
import PatientPanel from "../components/patient/PatientPanel";
import SoapEditor from "../components/note/SoapEditor";
import TranscriptViewer from "../components/transcript/TranscriptViewer";
import ValidationPanel from "../components/validation/ValidationPanel";
import { api } from "../services/api";
import type { Claim, ClinicalNote, Encounter, SoapSection } from "../types/clinical";

function noteFromClaims(claims: Claim[]): ClinicalNote {
  const by = (section: SoapSection) => claims.filter((claim) => claim.section === section);
  return {
    subjective: by("subjective"),
    objective: by("objective"),
    assessment: by("assessment"),
    plan: by("plan"),
  };
}

export default function EncounterPage() {
  const { encounterId } = useParams();
  const queryClient = useQueryClient();
  const [activeClaimId, setActiveClaimId] = useState<string | null>(null);
  const [activeSegmentId, setActiveSegmentId] = useState<string | null>(null);
  const [draftClaims, setDraftClaims] = useState<Claim[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [showFinalize, setShowFinalize] = useState(false);
  const [showAudit, setShowAudit] = useState(false);
  const [handoff, setHandoff] = useState<Record<string, unknown> | null>(null);

  const encounterQuery = useQuery({
    queryKey: ["encounter", encounterId],
    enabled: Boolean(encounterId),
    queryFn: () => api.getEncounter(encounterId!),
  });

  const save = useMutation({
    mutationFn: (claims: Claim[]) =>
      api.saveNote(encounterId!, {
        clinical_note: noteFromClaims(claims),
        claims,
        edit_reason: "Physician documentation edit",
      }),
    onSuccess: (data) => {
      setDraftClaims(null);
      queryClient.setQueryData(["encounter", encounterId], data);
      setError(null);
      toast.success("Draft saved", { description: "Your edits were recorded." });
    },
    onError: (err: Error) => {
      setError(err.message);
      toast.error("Save failed", { description: err.message });
    },
  });

  const finalize = useMutation({
    mutationFn: (acks: Record<string, boolean>) => api.finalize(encounterId!, acks),
    onSuccess: (data) => {
      queryClient.setQueryData(["encounter", encounterId], data);
      setShowFinalize(false);
      setError(null);
      toast.success("Note finalized", { description: "Audit log updated." });
    },
    onError: (err: Error) => {
      setError(err.message);
      toast.error("Finalize failed", { description: err.message });
    },
  });

  const ehr = useMutation({
    mutationFn: () => api.handoff(encounterId!),
    onSuccess: (data) => {
      setHandoff(data as Record<string, unknown>);
      toast.success("Sent to mock EHR", {
        description: `Status: ${String(data.status ?? "complete")}`,
      });
    },
    onError: (err: Error) => {
      setError(err.message);
      toast.error("EHR handoff failed", { description: err.message });
    },
  });

  const encounter = encounterQuery.data;
  const claims = draftClaims ?? encounter?.claims ?? [];

  const claimMap = useMemo(() => {
    const map = new Map(encounter?.validation.claims.map((item) => [item.claim_id, item]) ?? []);
    return map;
  }, [encounter]);

  useEffect(() => {
    if (error) {
      const t = setTimeout(() => setError(null), 4000);
      return () => clearTimeout(t);
    }
  }, [error]);

  function updateClaim(id: string, patch: Partial<Claim>) {
    setDraftClaims((current) => {
      const base = current ?? encounter?.claims ?? [];
      return base.map((claim) => (claim.id === id ? { ...claim, ...patch, origin: "physician" } : claim));
    });
  }

  function addClaim(section: SoapSection) {
    const id = `PHY-${Date.now()}`;
    setDraftClaims((current) => {
      const base = current ?? encounter?.claims ?? [];
      return [
        ...base,
        {
          id,
          text: "",
          section,
          citations: [],
          confidence: 1,
          origin: "physician",
          deleted: false,
        },
      ];
    });
  }

  function onCitation(segmentId: string, claimId: string) {
    setActiveClaimId(claimId);
    setActiveSegmentId(segmentId);
  }

  if (encounterQuery.isLoading) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-clinical-50">
        <div className="flex items-center gap-3 text-sm text-ink-600">
          <span className="h-5 w-5 animate-spin rounded-full border-2 border-clinical-200 border-t-clinical-700" />
          Loading encounter…
        </div>
      </div>
    );
  }

  if (encounterQuery.isError || !encounter) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-clinical-50 p-8">
        <motion.div
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          className="max-w-md rounded-2xl border border-ink-200 bg-white p-6 text-center shadow-lift"
        >
          <div className="mx-auto flex h-10 w-10 items-center justify-center rounded-full bg-red-50 text-red-700">
            <AlertCircle size={20} />
          </div>
          <h2 className="mt-3 text-sm font-semibold text-ink-900">Unable to load encounter</h2>
          <p className="mt-1 text-sm text-ink-600">
            The encounter could not be fetched. Please return to the worklist and try again.
          </p>
          <Link
            to="/"
            className="mt-4 inline-flex items-center gap-2 rounded-lg border border-ink-200 bg-white px-3 py-2 text-sm font-medium text-ink-700 hover:border-clinical-300 hover:text-clinical-800"
          >
            <ArrowLeft size={14} /> Return to worklist
          </Link>
        </motion.div>
      </div>
    );
  }

  const locked = encounter.workflow_status === "finalized";
  const critical = encounter.validation.critical_conflicts;

  return (
    <div className="flex min-h-screen flex-col">
      <HeaderBar encounter={encounter} />
      {error && (
        <motion.div
          initial={{ opacity: 0, y: -6 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0 }}
          className="border-b border-red-200 bg-red-50 px-4 py-2 text-sm text-red-800"
        >
          {error}
        </motion.div>
      )}
      <div className="grid flex-1 grid-cols-1 gap-3 p-3 xl:grid-cols-[300px_minmax(0,1fr)_360px]">
        <PatientPanel patient={encounter.patient} conflicts={encounter.validation.conflicts} />
        <SoapEditor
          claims={claims}
          validation={encounter.validation}
          locked={locked}
          activeClaimId={activeClaimId}
          onChange={updateClaim}
          onAdd={addClaim}
          onSelectClaim={(id) => {
            setActiveClaimId(id);
            const claim = claims.find((item) => item.id === id);
            if (claim?.citations[0]) setActiveSegmentId(claim.citations[0]);
          }}
          onCitation={onCitation}
        />
        <ValidationPanel
          encounter={encounter}
          activeClaimId={activeClaimId}
          onSelectClaim={(id, citations) => {
            setActiveClaimId(id);
            if (citations[0]) setActiveSegmentId(citations[0]);
          }}
        />
      </div>
      <TranscriptViewer
        segments={encounter.transcript.segments}
        activeSegmentId={activeSegmentId}
        onSelect={setActiveSegmentId}
        onUseEvidence={(segmentId) => {
          if (!activeClaimId || locked) return;
          updateClaim(activeClaimId, {
            citations: Array.from(
              new Set([
                ...(claims.find((c) => c.id === activeClaimId)?.citations ?? []),
                segmentId,
              ])
            ),
          });
          toast.success("Citation added", { description: `Linked to ${segmentId}` });
        }}
      />
      <ActionBar
        locked={locked}
        dirty={Boolean(draftClaims)}
        critical={critical}
        saving={save.isPending}
        onSave={() => save.mutate(claims)}
        onFinalize={() => setShowFinalize(true)}
        onPdf={() => {
          toast.message("Generating PDF…", { description: "Opening in a new tab." });
          window.open(api.pdfUrl(encounter.encounter_id), "_blank");
        }}
        onFhir={async () => {
          const bundle = await api.fhir(encounter.encounter_id);
          const blob = new Blob([JSON.stringify(bundle, null, 2)], { type: "application/fhir+json" });
          const url = URL.createObjectURL(blob);
          const a = document.createElement("a");
          a.href = url;
          a.download = `${encounter.encounter_id}-fhir.json`;
          a.click();
          URL.revokeObjectURL(url);
          toast.success("FHIR bundle downloaded");
        }}
        onHandoff={() => ehr.mutate()}
        onAudit={() => setShowAudit(true)}
        handoffBusy={ehr.isPending}
      />
      {handoff && (
        <motion.div
          initial={{ opacity: 0, y: 6 }}
          animate={{ opacity: 1, y: 0 }}
          className="border-t border-emerald-200 bg-emerald-50 px-4 py-2 text-sm text-emerald-900"
        >
          EHR handoff: {String(handoff.status ?? "complete")}. Clinical note submitted to mock EHR.
        </motion.div>
      )}
      {showFinalize && (
        <FinalizeDialog
          encounter={encounter as Encounter}
          unsupported={encounter.validation.summary.unsupported_claims}
          critical={critical}
          busy={finalize.isPending}
          onClose={() => setShowFinalize(false)}
          onConfirm={(acks) => finalize.mutate(acks)}
        />
      )}
      {showAudit && encounterId && (
        <AuditDrawer encounterId={encounterId} onClose={() => setShowAudit(false)} />
      )}
      <span className="hidden">{claimMap.size}</span>
    </div>
  );
}
