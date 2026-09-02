import type { Call } from "@/lib/types";

export function displayValue(value: unknown, fallback = "—"): string {
  if (typeof value === "string" && value.trim()) return value;
  if (typeof value === "number") return String(value);
  if (typeof value === "boolean") return value ? "Yes" : "No";
  return fallback;
}

export function resultValue(call: Call, ...keys: string[]): string {
  if (!call.result) return "—";
  for (const key of keys) {
    const value = call.result[key];
    if (value !== undefined && value !== null && value !== "") return displayValue(value);
  }
  return "—";
}

export function isCompleted(status: string): boolean {
  return ["COMPLETED", "COMPLETE", "SUCCESS", "SUCCEEDED"].includes(status.toUpperCase());
}

export function isInterested(call: Call): boolean {
  const interest = resultValue(call, "interest", "interest_level", "interested").toLowerCase();
  return ["yes", "true", "interested", "high", "very interested"].includes(interest);
}

export function formatDuration(seconds: number | null): string {
  if (seconds === null) return "—";
  const minutes = Math.floor(seconds / 60);
  const remainder = seconds % 60;
  return minutes ? `${minutes}m ${remainder}s` : `${remainder}s`;
}

export function formatDate(value: string): string {
  return new Intl.DateTimeFormat("en-IN", {
    day: "numeric",
    month: "short",
    hour: "2-digit",
    minute: "2-digit",
  }).format(new Date(value));
}
