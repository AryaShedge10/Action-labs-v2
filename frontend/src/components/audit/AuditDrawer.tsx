import { useQuery } from "@tanstack/react-query";
import { AnimatePresence, motion } from "framer-motion";
import { X } from "lucide-react";
import { api } from "../../services/api";
import { humanAction } from "../../utils/format";

export default function AuditDrawer({
  encounterId,
  onClose,
}: {
  encounterId: string;
  onClose: () => void;
}) {
  const audit = useQuery({
    queryKey: ["audit", encounterId],
    queryFn: () => api.audit(encounterId),
  });

  return (
    <AnimatePresence>
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
        className="fixed inset-0 z-50 flex justify-end bg-ink-900/40 backdrop-blur-sm"
        onClick={onClose}
      >
        <motion.aside
          initial={{ x: 32, opacity: 0 }}
          animate={{ x: 0, opacity: 1 }}
          exit={{ x: 32, opacity: 0 }}
          transition={{ duration: 0.3, ease: [0.22, 1, 0.36, 1] }}
          className="h-full w-full max-w-md overflow-auto bg-white p-5 shadow-lift"
          onClick={(e) => e.stopPropagation()}
        >
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-sm font-bold uppercase tracking-wide text-ink-900">Audit log</h2>
              <p className="mt-0.5 text-xs text-ink-500">
                Actions are recorded without writing full clinical records to application logs.
              </p>
            </div>
            <button
              onClick={onClose}
              className="rounded-md p-1 text-ink-500 hover:bg-ink-100 hover:text-ink-800"
              aria-label="Close"
            >
              <X size={16} />
            </button>
          </div>

          {audit.isLoading ? (
            <div className="mt-6 space-y-3">
              {[0, 1, 2, 3].map((i) => (
                <div key={i} className="h-12 rounded-lg shimmer" />
              ))}
            </div>
          ) : (
            <ol className="mt-4 space-y-3">
              {(audit.data ?? []).map((event, index) => (
                <motion.li
                  key={`${event.time}-${index}`}
                  initial={{ opacity: 0, x: 8 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ duration: 0.3, delay: index * 0.05 }}
                  className="relative rounded-r-lg border-l-2 border-clinical-600 bg-ink-100/40 py-2 pl-3 pr-2"
                >
                  <div className="text-[10px] uppercase tracking-wide text-ink-500">
                    {new Date(event.time).toLocaleString()} · {event.physician_id}
                  </div>
                  <div className="mt-0.5 text-sm font-semibold capitalize text-clinical-900">
                    {humanAction(event.action)}
                  </div>
                  <div className="text-xs text-ink-600">{event.detail}</div>
                </motion.li>
              ))}
              {audit.isSuccess && (audit.data ?? []).length === 0 && (
                <li className="text-xs text-ink-500">No audit events yet.</li>
              )}
            </ol>
          )}
        </motion.aside>
      </motion.div>
    </AnimatePresence>
  );
}
