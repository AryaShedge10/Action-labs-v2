import { motion } from "framer-motion";
import { useEffect, useRef } from "react";
import { Mic } from "lucide-react";
import type { TranscriptSegment } from "../../types/clinical";
import { formatClock } from "../../utils/format";

export default function TranscriptViewer({
  segments,
  activeSegmentId,
  onSelect,
  onUseEvidence,
}: {
  segments: TranscriptSegment[];
  activeSegmentId: string | null;
  onSelect: (id: string) => void;
  onUseEvidence: (id: string) => void;
}) {
  const refs = useRef<Record<string, HTMLElement | null>>({});

  useEffect(() => {
    if (activeSegmentId && refs.current[activeSegmentId]) {
      refs.current[activeSegmentId]?.scrollIntoView({ behavior: "smooth", block: "center" });
    }
  }, [activeSegmentId]);

  const active = segments.find((item) => item.id === activeSegmentId);

  return (
    <section className="border-t border-ink-200/70 bg-white/80 backdrop-blur-sm px-4 py-3">
      <div className="mb-2 flex items-baseline justify-between">
        <h2 className="text-xs font-semibold uppercase tracking-wide text-ink-500">
          Transcript / source evidence
        </h2>
        {active && (
          <span className="text-[11px] text-ink-500">
            {formatClock(active.start)}–{formatClock(active.end)} · {active.speaker} · confidence{" "}
            {Math.round(active.confidence * 100)}% · {active.source_type || "transcript"}
          </span>
        )}
      </div>
      <div className="scrollbar-thin flex max-h-44 gap-3 overflow-x-auto pb-1">
        {segments.map((segment, i) => {
          const isActive = activeSegmentId === segment.id;
          return (
            <motion.article
              key={segment.id}
              ref={(node) => {
                refs.current[segment.id] = node;
              }}
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.3, delay: i * 0.03, ease: [0.22, 1, 0.36, 1] }}
              whileHover={{ y: -2 }}
              className={`group min-w-[280px] max-w-sm shrink-0 cursor-pointer rounded-xl border p-3 text-xs transition-all ${
                isActive
                  ? "border-clinical-700 bg-clinical-50 shadow-lift ring-2 ring-clinical-200"
                  : "border-ink-200 bg-white hover:border-clinical-300 hover:shadow-soft"
              }`}
              onClick={() => onSelect(segment.id)}
            >
              <div className="flex items-center justify-between text-[10px] uppercase tracking-wide text-ink-500">
                <span className="inline-flex items-center gap-1">
                  <Mic size={10} />
                  {formatClock(segment.start)}
                </span>
                <span className="rounded-full bg-ink-100 px-1.5 py-0.5 font-semibold text-ink-700">
                  {segment.speaker}
                </span>
              </div>
              <p className="mt-2 text-sm leading-5 text-ink-800">“{segment.text}”</p>
              <div className="mt-2 flex items-center justify-between">
                <span className="text-[10px] text-ink-500">
                  confidence {Math.round(segment.confidence * 100)}%
                </span>
                <button
                  className="rounded-md border border-clinical-200 bg-clinical-50 px-2 py-0.5 text-[11px] font-semibold text-clinical-800 transition-colors hover:bg-clinical-100"
                  onClick={(event) => {
                    event.stopPropagation();
                    onSelect(segment.id);
                    onUseEvidence(segment.id);
                  }}
                >
                  Use as evidence
                </button>
              </div>
            </motion.article>
          );
        })}
      </div>
    </section>
  );
}
