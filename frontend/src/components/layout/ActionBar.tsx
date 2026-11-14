import { motion } from "framer-motion";
import { AlertTriangle, FileDown, FileText, ScrollText, Send, ShieldCheck } from "lucide-react";

export default function ActionBar({
  locked,
  dirty,
  critical,
  saving,
  handoffBusy,
  onSave,
  onFinalize,
  onPdf,
  onFhir,
  onHandoff,
  onAudit,
}: {
  locked: boolean;
  dirty: boolean;
  critical: number;
  saving: boolean;
  handoffBusy: boolean;
  onSave: () => void;
  onFinalize: () => void;
  onPdf: () => void;
  onFhir: () => void;
  onHandoff: () => void;
  onAudit: () => void;
}) {
  return (
    <motion.footer
      initial={{ y: 16, opacity: 0 }}
      animate={{ y: 0, opacity: 1 }}
      transition={{ duration: 0.35, ease: [0.22, 1, 0.36, 1] }}
      className="sticky bottom-0 z-10 flex flex-wrap items-center gap-2 border-t border-ink-200/70 glass px-4 py-3"
    >
      <PrimaryButton onClick={onSave} disabled={locked || saving}>
        {saving ? (
          <span className="inline-flex items-center gap-2">
            <span className="h-3.5 w-3.5 animate-spin rounded-full border-2 border-white/30 border-t-white" />
            Saving…
          </span>
        ) : (
          <span className="inline-flex items-center gap-2">
            <FileText size={14} /> Save draft
          </span>
        )}
      </PrimaryButton>

      <SecondaryButton
        onClick={onFinalize}
        disabled={locked || dirty}
        title={critical > 0 ? "Resolve critical conflicts before finalizing" : undefined}
      >
        <span className="inline-flex items-center gap-2">
          <ShieldCheck size={14} /> Finalize
        </span>
      </SecondaryButton>

      <SecondaryButton onClick={onPdf}>
        <span className="inline-flex items-center gap-2">
          <FileDown size={14} /> Download PDF
        </span>
      </SecondaryButton>

      <SecondaryButton onClick={onFhir}>
        <span className="inline-flex items-center gap-2">
          <FileDown size={14} /> FHIR JSON
        </span>
      </SecondaryButton>

      <SecondaryButton onClick={onHandoff} disabled={!locked || handoffBusy}>
        {handoffBusy ? (
          <span className="inline-flex items-center gap-2">
            <span className="h-3.5 w-3.5 animate-spin rounded-full border-2 border-clinical-300 border-t-clinical-700" />
            Sending…
          </span>
        ) : (
          <span className="inline-flex items-center gap-2">
            <Send size={14} /> Send to mock EHR
          </span>
        )}
      </SecondaryButton>

      <SecondaryButton onClick={onAudit}>
        <span className="inline-flex items-center gap-2">
          <ScrollText size={14} /> Audit trail
        </span>
      </SecondaryButton>

      <div className="ml-auto flex flex-wrap items-center gap-2 text-xs">
        {dirty && !locked && (
          <span className="inline-flex items-center gap-1 rounded-full border border-amber-200 bg-amber-50 px-2 py-0.5 font-semibold text-amber-800">
            Unsaved physician edits
          </span>
        )}
        {critical > 0 && !locked && (
          <span className="inline-flex items-center gap-1 rounded-full border border-red-200 bg-red-50 px-2 py-0.5 font-semibold text-red-700">
            <AlertTriangle size={12} />
            {critical} critical conflict{critical === 1 ? "" : "s"} — finalization blocked
          </span>
        )}
      </div>
    </motion.footer>
  );
}

function PrimaryButton({
  children,
  ...props
}: React.ButtonHTMLAttributes<HTMLButtonElement>) {
  return (
    <motion.button
      whileTap={{ scale: 0.97 }}
      className="rounded-xl bg-gradient-to-br from-clinical-700 to-clinical-900 px-3.5 py-2 text-sm font-semibold text-white shadow-soft hover:shadow-lift disabled:cursor-not-allowed disabled:opacity-50 disabled:hover:shadow-soft"
      {...props}
    >
      {children}
    </motion.button>
  );
}

function SecondaryButton({
  children,
  ...props
}: React.ButtonHTMLAttributes<HTMLButtonElement>) {
  return (
    <motion.button
      whileTap={{ scale: 0.97 }}
      className="rounded-xl border border-ink-200 bg-white px-3 py-2 text-sm font-medium text-ink-700 shadow-soft transition-colors hover:border-clinical-300 hover:text-clinical-800 disabled:cursor-not-allowed disabled:opacity-50"
      {...props}
    >
      {children}
    </motion.button>
  );
}
