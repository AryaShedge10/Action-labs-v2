import { motion } from "framer-motion";
import { AlertTriangle, ShieldAlert } from "lucide-react";
import type { Conflict, Patient } from "../../types/clinical";

export default function PatientPanel({
  patient,
  conflicts,
}: {
  patient: Patient;
  conflicts: Conflict[];
}) {
  const demographic = conflicts.filter((item) => item.category === "demographic" || item.category === "age");
  const allergy = conflicts.filter((item) => item.category === "allergy");

  return (
    <motion.aside
      initial={{ opacity: 0, x: -8 }}
      animate={{ opacity: 1, x: 0 }}
      transition={{ duration: 0.35, ease: [0.22, 1, 0.36, 1] }}
      className="rounded-2xl border border-ink-200/70 bg-white/90 p-4 text-sm shadow-soft"
    >
      <h2 className="text-xs font-semibold uppercase tracking-wide text-ink-500">
        Patient information
      </h2>
      <p className="mt-1 text-[11px] text-ink-500">
        Source of truth. Conflicts with generated text are flagged immediately.
      </p>
      <dl className="mt-3 divide-y divide-ink-100 rounded-lg border border-ink-200 bg-white">
        <Row label="Patient ID" value={patient.id} />
        <Row label="Name" value={patient.name} />
        <Row label="Age" value={String(patient.age)} />
        <Row label="Date of birth" value={patient.date_of_birth || "—"} />
        <Row label="Sex" value={patient.sex} />
        <Row label="Gender" value={patient.gender || "—"} />
      </dl>
      <Section title="Allergies" items={patient.allergies} danger />
      <Section title="Current medications" items={patient.medications} />
      <Section title="Medical history" items={patient.medical_history} />
      <Section title="Family history" items={patient.family_history} />
      <Section title="Known conditions" items={patient.known_conditions} />

      {(demographic.length > 0 || allergy.length > 0) && (
        <div className="mt-4 space-y-2">
          {allergy.map((item, i) => (
            <motion.div
              key={item.id}
              initial={{ opacity: 0, y: 6 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.3, delay: i * 0.05 }}
              className="flex items-start gap-2 rounded-lg border border-red-300 bg-red-50 p-2 text-xs text-red-900 shadow-soft"
            >
              <ShieldAlert size={14} className="mt-0.5 shrink-0" />
              <div>
                <div className="font-semibold">CRITICAL CONFLICT</div>
                {item.message}
              </div>
            </motion.div>
          ))}
          {demographic.map((item, i) => (
            <motion.div
              key={item.id}
              initial={{ opacity: 0, y: 6 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.3, delay: i * 0.05 }}
              className="flex items-start gap-2 rounded-lg border border-orange-300 bg-orange-50 p-2 text-xs text-orange-950 shadow-soft"
            >
              <AlertTriangle size={14} className="mt-0.5 shrink-0" />
              <div>
                <div className="font-semibold">{item.title}</div>
                {item.message}
              </div>
            </motion.div>
          ))}
        </div>
      )}
    </motion.aside>
  );
}

function Row({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex justify-between gap-3 px-3 py-1.5">
      <dt className="text-ink-500">{label}</dt>
      <dd className="font-medium text-ink-900">{value}</dd>
    </div>
  );
}

function Section({ title, items, danger }: { title: string; items: string[]; danger?: boolean }) {
  return (
    <div className="mt-4">
      <div className="text-xs font-semibold uppercase tracking-wide text-ink-500">{title}</div>
      <div className="mt-1 flex flex-wrap gap-1">
        {items.length === 0 && <span className="text-xs text-ink-400">None recorded</span>}
        {items.map((item) => (
          <span
            key={item}
            className={`rounded-full px-2 py-0.5 text-xs font-medium ${
              danger
                ? "bg-red-100 text-red-800 border border-red-200"
                : "bg-ink-100 text-ink-700 border border-ink-200"
            }`}
          >
            {item}
          </span>
        ))}
      </div>
    </div>
  );
}
