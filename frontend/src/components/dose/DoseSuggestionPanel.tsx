import { useQuery } from "@tanstack/react-query";
import { motion } from "framer-motion";
import { Pill } from "lucide-react";
import { useState } from "react";
import { api } from "../../services/api";
import type { DoseStatus, DoseSuggestion, Patient } from "../../types/clinical";

const STATUS_STYLE: Record<DoseStatus, string> = {
  SUGGESTED: "border-emerald-300 bg-emerald-50 text-emerald-900",
  NEEDS_INFO: "border-amber-300 bg-amber-50 text-amber-900",
  NOT_RECOMMENDED: "border-red-300 bg-red-50 text-red-900",
  NOT_SUPPORTED: "border-ink-300 bg-ink-50 text-ink-700",
};

// Facts the physician can supply to clear NEEDS_INFO. Everything stays unknown until typed.
const BOOLEAN_FIELDS: Record<string, string> = {
  "pregnant (or sex = male)": "pregnant",
  hepatic_impairment: "hepatic_impairment",
};
const NUMBER_FIELDS = new Set(["age_years", "weight_kg", "creatinine_clearance_ml_min"]);
const LIST_FIELDS = new Set(["allergies", "current_medications", "conditions"]);

function recordFacts(patient: Patient): Record<string, unknown> {
  const facts: Record<string, unknown> = {};
  if (patient.age != null) facts.age_years = patient.age;
  if (patient.sex) facts.sex = patient.sex.toLowerCase();
  if (patient.allergies?.length) facts.allergies = patient.allergies;
  if (patient.medications?.length) facts.current_medications = patient.medications;
  const history = [...(patient.medical_history ?? []), ...(patient.known_conditions ?? [])];
  if (history.length) facts.conditions = history.map((h) => h.toLowerCase());
  return facts;
}

function DoseCard({
  encounterId,
  drug,
  patient,
  locked,
}: {
  encounterId: string;
  drug: string;
  patient: Patient;
  locked: boolean;
}) {
  const [facts, setFacts] = useState<Record<string, unknown>>({});
  const [inputs, setInputs] = useState<Record<string, string>>({});
  const [editing, setEditing] = useState(false);
  const [editDose, setEditDose] = useState("");
  const [editUnit, setEditUnit] = useState("mg");
  const [recorded, setRecorded] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  const query = useQuery({
    queryKey: ["dose", encounterId, drug, facts],
    queryFn: () => api.doseSuggestion(encounterId, drug, { ...recordFacts(patient), ...facts }),
    retry: false,
  });
  const s: DoseSuggestion | undefined = query.data;

  function applyInputs() {
    const next: Record<string, unknown> = { ...facts };
    for (const key of s?.needs_info ?? []) {
      const raw = (inputs[key] ?? "").trim();
      if (!raw) continue;
      if (key in BOOLEAN_FIELDS) next[BOOLEAN_FIELDS[key]] = raw === "yes";
      else if (NUMBER_FIELDS.has(key)) next[key] = Number(raw);
      else if (LIST_FIELDS.has(key))
        next[key] = raw.toLowerCase() === "none" ? [] : raw.split(",").map((x) => x.trim().toLowerCase()).filter(Boolean);
    }
    setFacts(next);
  }

  async function decide(decision: "accepted" | "edited" | "rejected") {
    if (!s) return;
    setBusy(true);
    setErr(null);
    try {
      await api.doseDecision(encounterId, {
        drug,
        decision,
        suggestion: s,
        ...(decision === "edited" ? { edited_dose: Number(editDose), edited_unit: editUnit } : {}),
      });
      setRecorded(decision === "edited" ? `edited to ${editDose} ${editUnit}` : decision);
      setEditing(false);
    } catch (e) {
      setErr((e as Error).message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="rounded-xl border border-ink-200 bg-white p-3 text-sm">
      <div className="flex items-center justify-between gap-2">
        <div className="flex items-center gap-2 font-semibold capitalize text-ink-900">
          <Pill size={14} className="text-clinical-700" /> {drug}
        </div>
        {s && (
          <span className={`rounded-full border px-2 py-0.5 text-[11px] font-semibold ${STATUS_STYLE[s.status]}`}>
            {s.status.replace("_", " ")}
          </span>
        )}
      </div>
      {query.isLoading && <p className="mt-2 text-xs text-ink-500">Checking guideline…</p>}
      {query.isError && <p className="mt-2 text-xs text-red-700">{(query.error as Error).message}</p>}
      {s && (
        <>
          {s.status === "SUGGESTED" && (
            <dl className="mt-2 grid grid-cols-3 gap-2 text-xs">
              <div><dt className="text-ink-500">Start</dt><dd className="font-semibold">{s.start_dose} {s.unit}</dd></div>
              <div><dt className="text-ink-500">Max / day</dt><dd className="font-semibold">{s.max_daily_dose} {s.unit}</dd></div>
              <div><dt className="text-ink-500">Frequency</dt><dd className="font-semibold">{s.frequency}</dd></div>
              {s.titration_interval && (
                <div className="col-span-3"><dt className="text-ink-500">Titration</dt><dd>{s.titration_interval}</dd></div>
              )}
            </dl>
          )}
          {s.adjustments_applied.length > 0 && (
            <ul className="mt-2 list-disc space-y-0.5 pl-4 text-xs text-ink-700">
              {s.adjustments_applied.map((a) => <li key={a}>Adjusted: {a}</li>)}
            </ul>
          )}
          {s.reasons.length > 0 && (
            <ul className="mt-2 list-disc space-y-0.5 pl-4 text-xs text-red-800">
              {s.reasons.map((r) => <li key={r}>{r}</li>)}
            </ul>
          )}
          {s.needs_info.length > 0 && (
            <div className="mt-2 space-y-1.5 rounded-lg border border-amber-200 bg-amber-50/60 p-2 text-xs">
              <div className="font-semibold text-amber-900">Missing information (nothing is assumed):</div>
              {s.needs_info.map((key) => (
                <label key={key} className="flex items-center justify-between gap-2">
                  <span className="text-ink-700">{key}</span>
                  {key in BOOLEAN_FIELDS ? (
                    <select
                      className="rounded border border-ink-200 px-1 py-0.5"
                      value={inputs[key] ?? ""}
                      onChange={(e) => setInputs({ ...inputs, [key]: e.target.value })}
                    >
                      <option value="">unknown</option>
                      <option value="yes">yes</option>
                      <option value="no">no</option>
                    </select>
                  ) : (
                    <input
                      className="w-36 rounded border border-ink-200 px-1 py-0.5"
                      placeholder={LIST_FIELDS.has(key) ? "a, b  or  none" : "value"}
                      value={inputs[key] ?? ""}
                      onChange={(e) => setInputs({ ...inputs, [key]: e.target.value })}
                    />
                  )}
                </label>
              ))}
              <button onClick={applyInputs} className="rounded-md bg-clinical-700 px-2 py-1 font-medium text-white">
                Re-check
              </button>
            </div>
          )}
          {s.warnings.length > 0 && (
            <details className="mt-2 text-xs text-ink-700">
              <summary className="cursor-pointer font-medium">Warnings ({s.warnings.length})</summary>
              <ul className="mt-1 list-disc space-y-0.5 pl-4">{s.warnings.map((w) => <li key={w}>{w}</li>)}</ul>
            </details>
          )}
          {s.citations.length > 0 && (
            <details className="mt-1 text-xs text-ink-600">
              <summary className="cursor-pointer font-medium">Citations ({s.citations.length})</summary>
              <ul className="mt-1 space-y-0.5 pl-4">
                {s.citations.map((c) => (
                  <li key={`${c.page}-${c.supports}-${c.table_or_section}`}>
                    p{c.page} · {c.table_or_section} <span className="text-ink-400">({c.supports})</span>
                  </li>
                ))}
              </ul>
            </details>
          )}
          {recorded ? (
            <p className="mt-2 text-xs font-medium text-emerald-800">Recorded in audit log: {recorded}</p>
          ) : (
            <div className="mt-2 flex flex-wrap items-center gap-2">
              <button
                disabled={locked || busy || s.status !== "SUGGESTED"}
                onClick={() => decide("accepted")}
                className="rounded-md bg-emerald-600 px-2 py-1 text-xs font-medium text-white disabled:opacity-40"
              >
                Accept
              </button>
              <button
                disabled={locked || busy || s.status === "NOT_SUPPORTED"}
                onClick={() => { setEditing(true); setEditDose(s.start_dose != null ? String(s.start_dose) : ""); setEditUnit(s.unit ?? "mg"); }}
                className="rounded-md border border-ink-300 px-2 py-1 text-xs font-medium text-ink-800 disabled:opacity-40"
              >
                Edit
              </button>
              <button
                disabled={locked || busy}
                onClick={() => decide("rejected")}
                className="rounded-md border border-red-300 px-2 py-1 text-xs font-medium text-red-800 disabled:opacity-40"
              >
                Reject
              </button>
            </div>
          )}
          {editing && !recorded && (
            <div className="mt-2 flex items-center gap-2 text-xs">
              <input className="w-16 rounded border border-ink-200 px-1 py-0.5" value={editDose}
                     onChange={(e) => setEditDose(e.target.value)} placeholder="dose" />
              <input className="w-12 rounded border border-ink-200 px-1 py-0.5" value={editUnit}
                     onChange={(e) => setEditUnit(e.target.value)} />
              <button disabled={busy || !(Number(editDose) > 0)} onClick={() => decide("edited")}
                      className="rounded-md bg-clinical-700 px-2 py-1 font-medium text-white disabled:opacity-40">
                Save edit
              </button>
            </div>
          )}
          {err && <p className="mt-1 text-xs text-red-700">{err}</p>}
        </>
      )}
    </div>
  );
}

export default function DoseSuggestionPanel({
  encounterId,
  patient,
  locked,
}: {
  encounterId: string;
  patient: Patient;
  locked: boolean;
}) {
  const [manual, setManual] = useState<string[]>([]);
  const [draft, setDraft] = useState("");
  const prescribed = useQuery({
    queryKey: ["prescribed", encounterId],
    queryFn: () => api.prescribedDrugs(encounterId),
    retry: false,
  });
  const names = Array.from(
    new Set([...(prescribed.data ?? []).map((d) => d.medication.toLowerCase()), ...manual])
  );

  return (
    <motion.section
      initial={{ opacity: 0, x: 8 }}
      animate={{ opacity: 1, x: 0 }}
      className="rounded-2xl border border-ink-200/70 bg-white/90 p-4 shadow-soft"
      data-testid="dose-suggestion-panel"
    >
      <h2 className="text-xs font-semibold uppercase tracking-wide text-ink-500">Dose suggestion</h2>
      <p className="mt-1 rounded-md bg-amber-50 px-2 py-1 text-[11px] font-medium text-amber-900">
        Decision support prototype, not for clinical use. A suggestion for the doctor, never an order. Source: MoHFW STG
        Hypertension 2016 (not yet clinician-reviewed).
      </p>
      <form
        className="mt-3 flex gap-2"
        onSubmit={(e) => {
          e.preventDefault();
          const v = draft.trim().toLowerCase();
          if (v && !manual.includes(v)) setManual([...manual, v]);
          setDraft("");
        }}
      >
        <input
          className="min-w-0 flex-1 rounded-lg border border-ink-200 px-2 py-1 text-sm"
          placeholder="Check a drug, e.g. amlodipine"
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
        />
        <button className="rounded-lg bg-clinical-700 px-3 py-1 text-sm font-medium text-white">Check</button>
      </form>
      <div className="mt-3 space-y-3">
        {names.length === 0 && (
          <p className="text-xs text-ink-500">
            No prescribed drugs found for this encounter. Type a drug above to see the guideline dose.
          </p>
        )}
        {names.map((n) => (
          <DoseCard key={n} encounterId={encounterId} drug={n} patient={patient} locked={locked} />
        ))}
      </div>
    </motion.section>
  );
}
