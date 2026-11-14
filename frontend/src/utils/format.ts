export function formatClock(seconds: number): string {
  const total = Math.max(0, Math.floor(seconds));
  const m = Math.floor(total / 60)
    .toString()
    .padStart(2, "0");
  const s = (total % 60).toString().padStart(2, "0");
  return `${m}:${s}`;
}

export function cn(...parts: Array<string | false | null | undefined>): string {
  return parts.filter(Boolean).join(" ");
}

export function originLabel(origin: string, status?: string): string {
  if (status === "conflict") return "CONFLICT DETECTED";
  if (status === "unsupported") return "UNSUPPORTED";
  if (origin === "physician") return "PHYSICIAN EDITED";
  if (status === "supported") return "SOURCE VERIFIED";
  return "AI GENERATED";
}

export function humanAction(action: string): string {
  return action.replaceAll("_", " ");
}
