import { AnimatePresence, motion } from "framer-motion";
import { AlertTriangle, CheckCircle2, ShieldCheck, X } from "lucide-react";
import { useState } from "react";
import type { Encounter } from "../../types/clinical";

const ITEMS = [
  { key: "reviewed_documentation", label: "I have reviewed the generated clinical documentation." },
  { key: "reviewed_conflicts", label: "I have reviewed identified conflicts." },
  { key: "verified_medications_allergies", label: "I have verified medications and allergies." },
  { key: "approve_for_ehr_export", label: "I approve this note for EHR export." },
] as const;

export default function FinalizeDialog({
  encounter,
  unsupported,
  critical,
  busy,
  onClose,
  onConfirm,
}: {
  encounter: Encounter;
  unsupported: number;
  critical: number;
  busy: boolean;
  onClose: () => void;
  onConfirm: (acks: {
    reviewed_documentation: boolean;
    reviewed_conflicts: boolean;
    verified_medications_allergies: boolean;
    approve_for_ehr_export: boolean;
  }) => void;
}) {
  const [acks, setAcks] = useState({
    reviewed_documentation: false,
    reviewed_conflicts: false,
    verified_medications_allergies: false,
    approve_for_ehr_export: false,
  });
  const ready = Object.values(acks).every(Boolean) && critical === 0;
  const completed = Object.values(acks).filter(Boolean).length;
  const progress = (completed / ITEMS.length) * 100;

  return (
    <AnimatePresence>
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
        className="fixed inset-0 z-50 flex items-center justify-center bg-ink-900/40 p-4 backdrop-blur-sm"
        onClick={onClose}
      >
        <motion.div
          initial={{ opacity: 0, scale: 0.96, y: 12 }}
          animate={{ opacity: 1, scale: 1, y: 0 }}
          exit={{ opacity: 0, scale: 0.96, y: 12 }}
          transition={{ duration: 0.25, ease: [0.22, 1, 0.36, 1] }}
          className="w-full max-w-lg overflow-hidden rounded-2xl border border-ink-200 bg-white shadow-lift"
          onClick={(e) => e.stopPropagation()}
        >
          <div className="flex items-center justify-between border-b border-ink-100 bg-gradient-to-r from-clinical-50 to-white px-5 py-3">
            <div className="flex items-center gap-2">
              <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-clinical-100 text-clinical-800">
                <ShieldCheck size={16} />
              </div>
              <h2 className="text-sm font-bold text-ink-900">Physician confirmation</h2>
            </div>
            <button
              onClick={onClose}
              className="rounded-md p-1 text-ink-500 hover:bg-ink-100 hover:text-ink-800"
              aria-label="Close"
            >
              <X size={16} />
            </button>
          </div>

          <div className="px-5 py-4">
            <p className="text-sm text-ink-600">
              Encounter <span className="font-semibold text-ink-800">{encounter.encounter_id}</span>.
              AI-generated diagnoses, assessments, and prescriptions remain drafts until you approve
              them. This system does not replace clinical judgment.
            </p>

            {critical > 0 && (
              <div className="mt-3 flex items-start gap-2 rounded-lg border border-red-300 bg-red-50 p-2 text-sm text-red-800">
                <AlertTriangle size={14} className="mt-0.5 shrink-0" />
                <span>
                  Unable to finalize note. Critical validation conflict detected. Resolve or delete
                  the conflicting statements, then save the draft.
                </span>
              </div>
            )}
            {unsupported > 0 && (
              <div className="mt-3 flex items-start gap-2 rounded-lg border border-amber-300 bg-amber-50 p-2 text-sm text-amber-950">
                <AlertTriangle size={14} className="mt-0.5 shrink-0" />
                <span>
                  {unsupported} unsupported claim{unsupported === 1 ? "" : "s"} remain. Confirm you
                  have reviewed them before export.
                </span>
              </div>
            )}

            <div className="mt-3">
              <div className="mb-1.5 flex items-center justify-between text-xs text-ink-500">
                <span>Confirmations</span>
                <span className="font-semibold text-ink-700">
                  {completed} / {ITEMS.length}
                </span>
              </div>
              <div className="h-1.5 w-full overflow-hidden rounded-full bg-ink-100">
                <motion.div
                  className="h-full rounded-full bg-gradient-to-r from-clinical-600 to-clinical-800"
                  initial={{ width: 0 }}
                  animate={{ width: `${progress}%` }}
                  transition={{ duration: 0.35, ease: [0.22, 1, 0.36, 1] }}
                />
              </div>
            </div>

            <div className="mt-4 space-y-2">
              {ITEMS.map((item, i) => {
                const { key, label } = item;
                return (
                <motion.label
                  key={key}
                  initial={{ opacity: 0, y: 4 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ duration: 0.25, delay: 0.05 * i }}
                  className={`flex cursor-pointer items-start gap-2 rounded-lg border p-2 text-sm transition-colors ${
                    acks[key]
                      ? "border-clinical-200 bg-clinical-50/60"
                      : "border-ink-200 bg-white hover:border-clinical-200"
                  }`}
                >
                  <input
                    type="checkbox"
                    className="mt-0.5 h-4 w-4 rounded border-ink-300 text-clinical-700 focus:ring-clinical-500"
                    checked={acks[key]}
                    onChange={(event) =>
                      setAcks((current) => ({ ...current, [key]: event.target.checked }))
                    }
                  />
                  <span className="text-ink-700">{label}</span>
                  {acks[key] && (
                    <CheckCircle2
                      size={14}
                      className="ml-auto shrink-0 text-clinical-700"
                    />
                  )}
                </motion.label>
                );
              })}
            </div>
          </div>

          <div className="flex items-center justify-end gap-2 border-t border-ink-100 bg-ink-100/40 px-5 py-3">
            <button
              className="rounded-lg border border-ink-200 bg-white px-3 py-2 text-sm font-medium text-ink-700 hover:border-clinical-300 hover:text-clinical-800"
              onClick={onClose}
            >
              Cancel
            </button>
            <button
              className="inline-flex items-center gap-2 rounded-lg bg-gradient-to-br from-clinical-700 to-clinical-900 px-3 py-2 text-sm font-semibold text-white shadow-soft hover:shadow-lift disabled:cursor-not-allowed disabled:opacity-40 disabled:hover:shadow-soft"
              disabled={!ready || busy}
              onClick={() => onConfirm(acks)}
            >
              {busy ? (
                <>
                  <span className="h-3.5 w-3.5 animate-spin rounded-full border-2 border-white/30 border-t-white" />
                  Finalizing…
                </>
              ) : (
                <>
                  <ShieldCheck size={14} /> Finalize note
                </>
              )}
            </button>
          </div>
        </motion.div>
      </motion.div>
    </AnimatePresence>
  );
}
