import { AnimatePresence, motion } from "framer-motion";
import { Plus, Trash2 } from "lucide-react";
import type { Claim, SoapSection, ValidationResult } from "../../types/clinical";
import { originLabel } from "../../utils/format";

const SECTIONS: { key: SoapSection; label: string; helper: string }[] = [
  { key: "subjective", label: "Subjective", helper: "Patient-reported symptoms and history" },
  { key: "objective", label: "Objective", helper: "Examination findings, vitals, labs" },
  { key: "assessment", label: "Assessment", helper: "Working diagnoses and clinical reasoning" },
  { key: "plan", label: "Plan", helper: "Treatments, medications, follow-up" },
];

const BADGE_STYLES: Record<string, string> = {
  "CONFLICT DETECTED": "bg-red-100 text-red-800 border-red-200",
  UNSUPPORTED: "bg-amber-100 text-amber-900 border-amber-200",
  "PHYSICIAN EDITED": "bg-indigo-100 text-indigo-800 border-indigo-200",
  "SOURCE VERIFIED": "bg-emerald-100 text-emerald-800 border-emerald-200",
  "AI GENERATED": "bg-ink-100 text-ink-700 border-ink-200",
};

export default function SoapEditor({
  claims,
  validation,
  locked,
  activeClaimId,
  onChange,
  onAdd,
  onSelectClaim,
  onCitation,
}: {
  claims: Claim[];
  validation: ValidationResult;
  locked: boolean;
  activeClaimId: string | null;
  onChange: (id: string, patch: Partial<Claim>) => void;
  onAdd: (section: SoapSection) => void;
  onSelectClaim: (id: string) => void;
  onCitation: (segmentId: string, claimId: string) => void;
}) {
  const statusFor = (id: string) => validation.claims.find((item) => item.claim_id === id)?.status;

  return (
    <section className="rounded-2xl border border-ink-200/70 bg-white/95 p-4 shadow-soft">
      <div className="mb-3 flex items-baseline justify-between">
        <h2 className="text-xs font-semibold uppercase tracking-wide text-ink-500">
          Generated SOAP note
        </h2>
        <span className="text-[11px] text-ink-500">AI draft — physician editable</span>
      </div>
      <div className="space-y-5">
        {SECTIONS.map((section, sectionIndex) => (
          <motion.div
            key={section.key}
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.35, delay: sectionIndex * 0.05, ease: [0.22, 1, 0.36, 1] }}
          >
            <div className="mb-2 flex items-end justify-between border-b border-ink-200 pb-1">
              <div>
                <h3 className="text-sm font-semibold text-clinical-900">{section.label}</h3>
                <p className="text-[11px] text-ink-500">{section.helper}</p>
              </div>
              {!locked && (
                <button
                  className="inline-flex items-center gap-1 rounded-md border border-clinical-200 bg-clinical-50 px-2 py-1 text-[11px] font-semibold text-clinical-800 transition-colors hover:bg-clinical-100"
                  onClick={() => onAdd(section.key)}
                >
                  <Plus size={12} /> Add statement
                </button>
              )}
            </div>
            <div className="space-y-2">
              <AnimatePresence initial={false}>
                {claims
                  .filter((claim) => claim.section === section.key && !claim.deleted)
                  .map((claim) => {
                    const status = statusFor(claim.id);
                    const badge = originLabel(claim.origin, status);
                    return (
                      <motion.article
                        key={claim.id}
                        layout
                        initial={{ opacity: 0, y: 6 }}
                        animate={{ opacity: 1, y: 0 }}
                        exit={{ opacity: 0, scale: 0.98 }}
                        transition={{ duration: 0.22, ease: [0.22, 1, 0.36, 1] }}
                        className={`group cursor-pointer rounded-xl border p-3 transition-all ${
                          activeClaimId === claim.id
                            ? "border-clinical-700 bg-clinical-50/70 shadow-soft"
                            : "border-ink-200 bg-white hover:border-clinical-300 hover:shadow-soft"
                        }`}
                        onClick={() => onSelectClaim(claim.id)}
                      >
                        <div className="mb-2 flex flex-wrap items-center gap-2">
                          <span
                            className={`rounded-full border px-2 py-0.5 text-[10px] font-semibold tracking-wide ${
                              BADGE_STYLES[badge] ?? BADGE_STYLES["AI GENERATED"]
                            }`}
                          >
                            {badge}
                          </span>
                          {(!claim.citations || claim.citations.length === 0) && (
                            <span className="text-[10px] font-medium text-amber-800">
                              ⚠ UNGROUNDED CLAIM — no supporting transcript evidence found.
                            </span>
                          )}
                        </div>
                        <textarea
                          className="w-full resize-y rounded-lg border border-ink-200 bg-white p-2 text-sm leading-6"
                          rows={2}
                          disabled={locked}
                          value={claim.text}
                          onChange={(event) => onChange(claim.id, { text: event.target.value })}
                        />
                        <div className="mt-2 flex flex-wrap items-center gap-2">
                          {claim.citations.map((citation) => (
                            <motion.button
                              key={citation}
                              whileHover={{ y: -1 }}
                              whileTap={{ scale: 0.95 }}
                              className="rounded-full border border-clinical-200 bg-clinical-50 px-2 py-0.5 text-[11px] font-semibold text-clinical-800 hover:bg-clinical-100"
                              onClick={(event) => {
                                event.stopPropagation();
                                onCitation(citation, claim.id);
                              }}
                            >
                              Citation #{citation.replace(/\D/g, "") || citation}
                            </motion.button>
                          ))}
                          {!locked && (
                            <button
                              className="ml-auto inline-flex items-center gap-1 rounded-md border border-red-200 bg-red-50 px-2 py-1 text-[11px] font-semibold text-red-700 transition-colors hover:bg-red-100"
                              onClick={(e) => {
                                e.stopPropagation();
                                onChange(claim.id, { deleted: true });
                              }}
                            >
                              <Trash2 size={12} /> Delete
                            </button>
                          )}
                        </div>
                      </motion.article>
                    );
                  })}
              </AnimatePresence>
            </div>
          </motion.div>
        ))}
      </div>
    </section>
  );
}
