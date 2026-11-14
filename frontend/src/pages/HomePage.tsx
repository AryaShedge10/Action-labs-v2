import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { motion } from "framer-motion";
import {
  ArrowRight,
  FileText,
  Lock,
  PlayCircle,
  ShieldCheck,
  Sparkles,
  Stethoscope,
} from "lucide-react";
import { useNavigate } from "react-router-dom";
import { toast } from "sonner";
import { api } from "../services/api";
import AudioRecorder from "../components/audio/AudioRecorder";

const features = [
  {
    icon: Sparkles,
    title: "AI drafts, physician finals",
    body: "SOAP notes are generated from the encounter transcript. Nothing is finalized until you approve it.",
  },
  {
    icon: ShieldCheck,
    title: "Built-in safety checks",
    body: "Allergy, demographic, age, and grounding conflicts surface in the validation panel before export.",
  },
  {
    icon: Lock,
    title: "Local & private",
    body: "No PHI leaves your network. Configure a private model endpoint inside your trust boundary.",
  },
];

export default function HomePage() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const list = useQuery({ queryKey: ["encounters"], queryFn: api.listEncounters });
  const demo = useMutation({
    mutationFn: api.loadDemo,
    onSuccess: (encounter) => {
      queryClient.invalidateQueries({ queryKey: ["encounters"] });
      toast.success("Demo encounter loaded", {
        description: `Opening ${encounter.encounter_id}`,
      });
      navigate(`/encounters/${encounter.encounter_id}`);
    },
    onError: (err: Error) => toast.error("Could not load demo", { description: err.message }),
  });

  return (
    <div className="min-h-screen">
      <header className="sticky top-0 z-30 border-b border-ink-200/70 glass">
        <div className="mx-auto flex max-w-6xl items-center justify-between px-6 py-4">
          <motion.div
            initial={{ opacity: 0, x: -8 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ duration: 0.4, ease: [0.22, 1, 0.36, 1] }}
            className="flex items-center gap-3"
          >
            <div className="relative flex h-10 w-10 items-center justify-center rounded-xl bg-gradient-to-br from-clinical-700 to-clinical-900 text-white shadow-soft">
              <Stethoscope size={20} />
              <span className="absolute -right-1 -top-1 inline-flex h-3 w-3">
                <span className="absolute inline-flex h-full w-full animate-pulse-ring rounded-full bg-emerald-400" />
                <span className="relative inline-flex h-3 w-3 rounded-full bg-emerald-500" />
              </span>
            </div>
            <div>
              <div className="text-sm font-bold tracking-wide text-clinical-900">CLINICAL SCRIBE</div>
              <div className="text-xs text-ink-500">EHR Interface &amp; Clinical Validation Dashboard</div>
            </div>
          </motion.div>
          <motion.div
            initial={{ opacity: 0, x: 8 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ duration: 0.4, ease: [0.22, 1, 0.36, 1] }}
            className="inline-flex items-center gap-2 rounded-full border border-emerald-200 bg-emerald-50/80 px-3 py-1 text-xs font-semibold text-emerald-800 shadow-soft"
          >
            <Lock size={12} />
            Local / Private Processing
          </motion.div>
        </div>
      </header>

      <main className="mx-auto max-w-6xl px-6 py-10">
        <section className="grid gap-8 lg:grid-cols-[1.2fr_1fr] lg:items-center">
          <motion.div
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5, ease: [0.22, 1, 0.36, 1] }}
          >
            <span className="inline-flex items-center gap-2 rounded-full border border-clinical-200 bg-clinical-50 px-3 py-1 text-xs font-semibold text-clinical-800">
              <Sparkles size={12} /> Physician-first documentation
            </span>
            <h1 className="mt-4 text-4xl font-extrabold leading-tight tracking-tight text-ink-900 sm:text-5xl">
              Validate every AI draft <br className="hidden sm:block" />
              <span className="bg-gradient-to-r from-clinical-700 to-clinical-500 bg-clip-text text-transparent">
                before it touches the chart.
              </span>
            </h1>
            <p className="mt-4 max-w-2xl text-base leading-7 text-ink-600">
              Clinical Scribe turns the patient–physician transcript into a SOAP draft, then puts the
              physician in control with citations, grounding checks, and a four-step finalize gate.
              This software does not independently diagnose, prescribe, or replace clinical judgment.
            </p>
            <div className="mt-6 flex flex-wrap items-center gap-3">
              <motion.button
                whileHover={{ scale: 1.02 }}
                whileTap={{ scale: 0.98 }}
                onClick={() => demo.mutate()}
                disabled={demo.isPending}
                className="group inline-flex items-center gap-2 rounded-xl bg-gradient-to-br from-clinical-700 to-clinical-900 px-5 py-3 text-sm font-semibold text-white shadow-lift hover:shadow-ring disabled:opacity-50"
              >
                {demo.isPending ? (
                  <>
                    <span className="h-4 w-4 animate-spin rounded-full border-2 border-white/30 border-t-white" />
                    Loading demo…
                  </>
                ) : (
                  <>
                    <PlayCircle size={16} /> Load Demo Encounter
                    <ArrowRight
                      size={16}
                      className="transition-transform group-hover:translate-x-0.5"
                    />
                  </>
                )}
              </motion.button>
              <a
                href="https://github.com"
                onClick={(e) => e.preventDefault()}
                className="inline-flex items-center gap-2 rounded-xl border border-ink-200 bg-white px-4 py-3 text-sm font-medium text-ink-700 shadow-soft hover:border-clinical-300 hover:text-clinical-800"
              >
                <FileText size={16} /> View docs
              </a>
            </div>
            {demo.isError && (
              <p className="mt-3 text-sm text-red-700">
                {(demo.error as Error).message || "Unable to load encounter."}
              </p>
            )}
          </motion.div>

          <motion.div
            initial={{ opacity: 0, y: 16 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.55, ease: [0.22, 1, 0.36, 1], delay: 0.05 }}
            className="relative"
          >
            <div className="absolute -inset-4 -z-10 rounded-3xl bg-gradient-to-br from-clinical-200/60 to-transparent blur-xl" />
            <div className="rounded-2xl border border-ink-200/70 bg-white/90 p-5 shadow-lift">
              <div className="flex items-center justify-between">
                <div className="text-xs font-semibold uppercase tracking-wide text-ink-500">
                  Today's preview
                </div>
                <span className="rounded-full bg-amber-100 px-2 py-0.5 text-[10px] font-semibold text-amber-800">
                  CRITICAL
                </span>
              </div>
              <div className="mt-3 space-y-2">
                <PreviewLine label="Patient" value="John Doe · 42M" />
                <PreviewLine label="Allergy" value="Penicillin" tone="danger" />
                <PreviewLine label="Draft diagnosis" value="Asthma" tone="warn" />
                <PreviewLine label="Proposed Rx" value="Amoxicillin" tone="danger" />
              </div>
              <div className="mt-4 rounded-lg border border-ink-200 bg-ink-100/60 p-3 text-xs text-ink-600">
                The validation panel will block finalization until critical conflicts are resolved.
              </div>
            </div>
          </motion.div>
        </section>

        <section className="mt-8">
          <AudioRecorder
            onSuccess={(encounter) => {
              queryClient.invalidateQueries({ queryKey: ["encounters"] });
              navigate(`/encounters/${encounter.encounter_id}`);
            }}
          />
        </section>

        <section className="mt-12 grid gap-4 sm:grid-cols-3">
          {features.map((feature, i) => (
            <motion.div
              key={feature.title}
              initial={{ opacity: 0, y: 12 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.4, ease: [0.22, 1, 0.36, 1], delay: 0.1 + i * 0.06 }}
              className="group rounded-2xl border border-ink-200/70 bg-white/80 p-5 shadow-soft transition-all hover:-translate-y-0.5 hover:border-clinical-300 hover:shadow-lift"
            >
              <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-clinical-50 text-clinical-700 transition-colors group-hover:bg-clinical-100">
                <feature.icon size={18} />
              </div>
              <div className="mt-3 text-sm font-semibold text-ink-900">{feature.title}</div>
              <p className="mt-1 text-sm leading-6 text-ink-600">{feature.body}</p>
            </motion.div>
          ))}
        </section>

        <section className="mt-12">
          <div className="mb-4 flex items-end justify-between">
            <div>
              <h2 className="text-lg font-semibold text-ink-900">Physician worklist</h2>
              <p className="text-sm text-ink-500">Open an encounter to validate, edit, and finalize.</p>
            </div>
            {list.isFetching && (
              <span className="text-xs text-ink-500">Refreshing…</span>
            )}
          </div>

          <div className="overflow-hidden rounded-2xl border border-ink-200/70 bg-white/90 shadow-soft">
            {list.isLoading ? (
              <div className="space-y-2 p-4">
                {[0, 1, 2].map((i) => (
                  <div key={i} className="h-10 rounded-lg shimmer" />
                ))}
              </div>
            ) : (
              <table className="w-full text-left text-sm">
                <thead className="bg-ink-100/60 text-xs uppercase tracking-wide text-ink-500">
                  <tr>
                    <th className="px-4 py-3">Encounter</th>
                    <th className="px-4 py-3">Patient ID</th>
                    <th className="px-4 py-3">Physician</th>
                    <th className="px-4 py-3">AI status</th>
                    <th className="px-4 py-3">Validation</th>
                    <th className="px-4 py-3">Workflow</th>
                    <th className="px-4 py-3" />
                  </tr>
                </thead>
                <tbody>
                  {(list.data ?? []).map((row, i) => (
                    <motion.tr
                      key={row.encounter_id}
                      initial={{ opacity: 0, y: 6 }}
                      animate={{ opacity: 1, y: 0 }}
                      transition={{ duration: 0.3, delay: i * 0.04 }}
                      onClick={() => navigate(`/encounters/${row.encounter_id}`)}
                      className="group cursor-pointer border-t border-ink-200/60 transition-colors hover:bg-clinical-50/70"
                    >
                      <td className="px-4 py-3 font-semibold text-clinical-900">
                        {row.encounter_id}
                      </td>
                      <td className="px-4 py-3 text-ink-700">{row.patient_id}</td>
                      <td className="px-4 py-3 text-ink-700">{row.physician_name}</td>
                      <td className="px-4 py-3">
                        <StatusPill tone="info">{row.ai_status.replaceAll("_", " ")}</StatusPill>
                      </td>
                      <td className="px-4 py-3">
                        <StatusPill tone="muted">{row.validation_status}</StatusPill>
                      </td>
                      <td className="px-4 py-3">
                        <StatusPill tone={row.workflow_status === "finalized" ? "success" : "warn"}>
                          {row.workflow_status}
                        </StatusPill>
                      </td>
                      <td className="px-4 py-3 text-right">
                        <ArrowRight
                          size={16}
                          className="ml-auto text-ink-400 transition-transform group-hover:translate-x-1 group-hover:text-clinical-700"
                        />
                      </td>
                    </motion.tr>
                  ))}
                  {list.isSuccess && list.data.length === 0 && (
                    <tr>
                      <td className="px-4 py-10 text-center text-ink-500" colSpan={7}>
                        No encounters yet. Load the synthetic demo to begin physician review.
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            )}
          </div>
        </section>
      </main>
    </div>
  );
}

function PreviewLine({
  label,
  value,
  tone = "default",
}: {
  label: string;
  value: string;
  tone?: "default" | "danger" | "warn";
}) {
  const toneClass =
    tone === "danger"
      ? "text-red-700"
      : tone === "warn"
      ? "text-amber-800"
      : "text-ink-800";
  return (
    <div className="flex items-center justify-between rounded-lg border border-ink-200 bg-white px-3 py-2">
      <span className="text-xs font-medium text-ink-500">{label}</span>
      <span className={`text-sm font-semibold ${toneClass}`}>{value}</span>
    </div>
  );
}

function StatusPill({
  children,
  tone = "muted",
}: {
  children: React.ReactNode;
  tone?: "muted" | "info" | "success" | "warn" | "danger";
}) {
  const map: Record<string, string> = {
    muted: "bg-ink-100 text-ink-700 border-ink-200",
    info: "bg-clinical-50 text-clinical-800 border-clinical-200",
    success: "bg-emerald-50 text-emerald-800 border-emerald-200",
    warn: "bg-amber-50 text-amber-800 border-amber-200",
    danger: "bg-red-50 text-red-800 border-red-200",
  };
  return (
    <span
      className={`inline-flex items-center rounded-full border px-2 py-0.5 text-[11px] font-semibold capitalize ${map[tone]}`}
    >
      {children}
    </span>
  );
}
