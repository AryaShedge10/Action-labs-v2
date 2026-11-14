import { Lock } from "lucide-react";
import { Link } from "react-router-dom";
import { motion } from "framer-motion";
import type { Encounter } from "../../types/clinical";

function StatusDot({ ok, label }: { ok: boolean; label: string }) {
  return (
    <span className="inline-flex items-center gap-1.5 rounded-full border border-ink-200 bg-white/70 px-2 py-0.5 text-xs text-ink-700 shadow-soft">
      <span className="relative inline-flex h-2 w-2">
        {ok ? (
          <>
            <span className="absolute inline-flex h-full w-full animate-pulse-ring rounded-full bg-emerald-400" />
            <span className="relative inline-flex h-2 w-2 rounded-full bg-emerald-500" />
          </>
        ) : (
          <>
            <span className="absolute inline-flex h-full w-full animate-pulse-ring rounded-full bg-amber-400" />
            <span className="relative inline-flex h-2 w-2 rounded-full bg-amber-500" />
          </>
        )}
      </span>
      {label}
    </span>
  );
}

export default function HeaderBar({ encounter }: { encounter: Encounter }) {
  const date = new Date(encounter.encounter_at);
  return (
    <motion.header
      initial={{ y: -12, opacity: 0 }}
      animate={{ y: 0, opacity: 1 }}
      transition={{ duration: 0.35, ease: [0.22, 1, 0.36, 1] }}
      className="sticky top-0 z-20 border-b border-ink-200/70 glass"
    >
      <div className="flex flex-wrap items-center justify-between gap-3 px-4 py-3">
        <div className="flex flex-wrap items-center gap-4">
          <Link
            to="/"
            className="text-sm font-extrabold tracking-wide text-clinical-900 hover:text-clinical-700"
          >
            CLINICAL SCRIBE
          </Link>
          <div className="hidden h-6 w-px bg-ink-200 sm:block" />
          <div className="text-sm text-ink-700">
            <span className="text-ink-500">Patient</span>{" "}
            <span className="font-semibold text-ink-900">{encounter.patient.name}</span>
            <span className="mx-2 text-ink-300">|</span>
            <span className="text-ink-500">ID</span> {encounter.patient.id}
            <span className="mx-2 text-ink-300">|</span>
            <span className="text-ink-500">Encounter</span> {encounter.encounter_id}
          </div>
        </div>
        <div className="flex flex-wrap items-center gap-3 text-xs text-ink-600">
          <span>
            {date.toLocaleString()} · <span className="font-medium">{encounter.physician_name}</span>
          </span>
          <StatusDot ok={encounter.ai_status !== "processing"} label="AI Draft Ready" />
          <StatusDot
            ok={encounter.workflow_status === "finalized"}
            label={
              encounter.workflow_status === "finalized" ? "Finalized" : "Validation Required"
            }
          />
          <span className="inline-flex items-center gap-1 rounded-full border border-emerald-200 bg-emerald-50 px-2 py-0.5 font-semibold text-emerald-800">
            <Lock size={12} />
            {encounter.privacy.label}
          </span>
        </div>
      </div>
    </motion.header>
  );
}
