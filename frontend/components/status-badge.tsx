import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";

export function StatusBadge({ status }: { status: string }) {
  const normalized = status.toUpperCase();
  const complete = ["COMPLETED", "COMPLETE", "SUCCESS", "SUCCEEDED"].includes(normalized);
  const failed = ["FAILED", "ERROR", "CANCELLED"].includes(normalized);
  return (
    <Badge className={cn(complete && "bg-emerald-100 text-emerald-700", failed && "bg-red-100 text-red-700", !complete && !failed && "bg-amber-100 text-amber-700")}>
      {status.replaceAll("_", " ")}
    </Badge>
  );
}
