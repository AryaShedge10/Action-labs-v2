import { motion } from "framer-motion";
import { Cell, Pie, PieChart, ResponsiveContainer } from "recharts";
import { AlertCircle, CheckCircle2, ShieldAlert } from "lucide-react";
import type { Encounter } from "../../types/clinical";

const SEVERITY: Record<string, { wrap: string; icon: React.ReactNode }> = {
  CRITICAL: {
    wrap: "border-red-300 bg-red-50 text-red-900 hover:bg-red-100/70",
    icon: <ShieldAlert size={14} className="mt-0.5 shrink-0" />,
  },
  HIGH: {
    wrap: "border-orange-300 bg-orange-50 text-orange-950 hover:bg-orange-100/70",
    icon: <AlertCircle size={14} className="mt-0.5 shrink-0" />,
  },
  MEDIUM: {
    wrap: "border-amber-300 bg-amber-50 text-amber-950 hover:bg-amber-100/70",
    icon: <AlertCircle size={14} className="mt-0.5 shrink-0" />,
  },
  LOW: {
    wrap: "border-ink-200 bg-ink-50 text-ink-700 hover:bg-ink-100/70",
    icon: <CheckCircle2 size={14} className="mt-0.5 shrink-0" />,
  },
};

export default function ValidationPanel({
  encounter,
  activeClaimId,
  onSelectClaim,
}: {
  encounter: Encounter;
  activeClaimId: string | null;
  onSelectClaim: (id: string, citations: string[]) => void;
}) {
  const { summary, conflicts, claims, critical_conflicts } = encounter.validation;
  const supported = Math.max(0, summary.supported_claims);
  const total = Math.max(summary.total_claims, 1);
  const groundingPct = Math.min(100, Math.max(0, summary.grounding_score));
  const chart = [
    { name: "Supported", value: supported },
    { name: "Other", value: Math.max(total - supported, 0) },
  ];

  return (
    <aside className="space-y-3">
      <motion.section
        initial={{ opacity: 0, y: 8 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.35, ease: [0.22, 1, 0.36, 1] }}
        className="rounded-2xl border border-ink-200/70 bg-white/95 p-4 shadow-soft"
      >
        <h2 className="text-xs font-semibold uppercase tracking-wide text-ink-500">AI validation</h2>
        <p className="mt-1 text-[11px] leading-4 text-ink-500">{summary.disclaimer}</p>

        <div className="mt-3 flex items-center gap-4">
          <div className="relative h-24 w-24">
            <ResponsiveContainer>
              <PieChart>
                <Pie
                  data={chart}
                  dataKey="value"
                  innerRadius={30}
                  outerRadius={44}
                  stroke="none"
                  startAngle={90}
                  endAngle={-270}
                >
                  <Cell fill="#1c6c8a" />
                  <Cell fill="#e2e8f0" />
                </Pie>
              </PieChart>
            </ResponsiveContainer>
            <div className="pointer-events-none absolute inset-0 flex flex-col items-center justify-center">
              <motion.div
                key={groundingPct}
                initial={{ scale: 0.85, opacity: 0 }}
                animate={{ scale: 1, opacity: 1 }}
                transition={{ duration: 0.3 }}
                className="text-xl font-extrabold text-clinical-900"
              >
                {groundingPct}%
              </motion.div>
              <div className="text-[10px] uppercase tracking-wide text-ink-500">Grounded</div>
            </div>
          </div>
          <div className="flex-1 space-y-1.5 text-xs">
            <Stat label="Citation coverage" value={`${summary.citation_coverage}%`} />
            <Stat label="Supported" value={summary.supported_claims} tone="success" />
            <Stat label="Unsupported" value={summary.unsupported_claims} tone="warn" />
            <Stat label="Contradictory" value={summary.contradictory_claims} tone="danger" />
            <Stat label="Critical" value={critical_conflicts} tone="danger" bold />
          </div>
        </div>

        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.15 }}
          className="mt-3 rounded-lg border border-amber-200 bg-amber-50 px-2 py-1.5 text-xs font-medium text-amber-950"
        >
          Status: {encounter.validation.banner}
        </motion.div>
      </motion.section>

      <motion.section
        initial={{ opacity: 0, y: 8 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.35, ease: [0.22, 1, 0.36, 1], delay: 0.05 }}
        className="rounded-2xl border border-ink-200/70 bg-white/95 p-4 shadow-soft"
      >
        <h2 className="text-xs font-semibold uppercase tracking-wide text-ink-500">Conflicts</h2>
        <div className="mt-2 max-h-52 space-y-2 overflow-auto pr-1 scrollbar-thin">
          {conflicts.length === 0 && (
            <p className="text-xs text-ink-500">No deterministic conflicts.</p>
          )}
          {conflicts.map((item, i) => {
            const style = SEVERITY[item.severity] ?? SEVERITY.LOW;
            return (
              <motion.button
                key={item.id}
                initial={{ opacity: 0, y: 6 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.3, delay: i * 0.04 }}
                whileHover={{ x: 2 }}
                className={`flex w-full items-start gap-2 rounded-lg border p-2 text-left text-xs transition-colors ${style.wrap}`}
                onClick={() => item.claim_id && onSelectClaim(item.claim_id, [])}
              >
                {style.icon}
                <span>
                  <span className="font-semibold">
                    {item.severity} · {item.title}
                  </span>
                  <div className="mt-0.5 leading-5">{item.message}</div>
                </span>
              </motion.button>
            );
          })}
        </div>
      </motion.section>

      <motion.section
        initial={{ opacity: 0, y: 8 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.35, ease: [0.22, 1, 0.36, 1], delay: 0.1 }}
        className="rounded-2xl border border-ink-200/70 bg-white/95 p-4 shadow-soft"
      >
        <h2 className="text-xs font-semibold uppercase tracking-wide text-ink-500">
          Claim-level validation
        </h2>
        <div className="mt-2 max-h-64 overflow-auto pr-1 scrollbar-thin">
          <table className="w-full text-left text-[11px]">
            <thead className="sticky top-0 bg-white text-ink-500">
              <tr>
                <th className="pb-1 font-semibold">Claim</th>
                <th className="pb-1 font-semibold">Evidence</th>
                <th className="pb-1 font-semibold">Status</th>
              </tr>
            </thead>
            <tbody>
              {claims
                .filter((item) => !item.deleted)
                .map((item) => {
                  const tone =
                    item.status === "supported"
                      ? "bg-emerald-100 text-emerald-800 border-emerald-200"
                      : item.status === "conflict"
                      ? "bg-red-100 text-red-800 border-red-200"
                      : item.status === "unsupported"
                      ? "bg-amber-100 text-amber-900 border-amber-200"
                      : "bg-ink-100 text-ink-700 border-ink-200";
                  return (
                    <tr
                      key={item.claim_id}
                      className={`cursor-pointer border-t border-ink-100 transition-colors ${
                        activeClaimId === item.claim_id ? "bg-clinical-50" : "hover:bg-clinical-50/60"
                      }`}
                      onClick={() => onSelectClaim(item.claim_id, item.citations)}
                    >
                      <td className="py-1.5 pr-2 align-top text-ink-800">{item.text}</td>
                      <td className="py-1.5 align-top text-ink-600">
                        {item.citations[0] ?? (
                          <span className="text-ink-400">None</span>
                        )}
                      </td>
                      <td className="py-1.5 align-top">
                        <span
                          className={`inline-flex items-center rounded-full border px-1.5 py-0.5 text-[10px] font-semibold capitalize ${tone}`}
                        >
                          {item.status}
                        </span>
                      </td>
                    </tr>
                  );
                })}
            </tbody>
          </table>
        </div>
      </motion.section>
    </aside>
  );
}

function Stat({
  label,
  value,
  tone = "muted",
  bold = false,
}: {
  label: string;
  value: string | number;
  tone?: "muted" | "success" | "warn" | "danger";
  bold?: boolean;
}) {
  const map: Record<string, string> = {
    muted: "text-ink-700",
    success: "text-emerald-700",
    warn: "text-amber-800",
    danger: "text-red-700",
  };
  return (
    <div className="flex items-center justify-between">
      <span className="text-ink-500">{label}</span>
      <span className={`${map[tone]} ${bold ? "font-bold" : "font-semibold"}`}>{value}</span>
    </div>
  );
}
