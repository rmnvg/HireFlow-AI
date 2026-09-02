import { AlertCircle, CheckCircle2, Info } from "lucide-react";

import { cn } from "@/lib/utils";

type AlertVariant = "error" | "info" | "success";

export function Alert({ children, variant = "info" }: { children: React.ReactNode; variant?: AlertVariant }) {
  const Icon = variant === "error" ? AlertCircle : variant === "success" ? CheckCircle2 : Info;
  return (
    <div className={cn("flex gap-3 rounded-xl border p-3.5 text-sm leading-5", variant === "error" && "border-red-200 bg-red-50 text-red-800", variant === "info" && "border-blue-200 bg-blue-50 text-blue-800", variant === "success" && "border-emerald-200 bg-emerald-50 text-emerald-800")} role={variant === "error" ? "alert" : "status"}>
      <Icon className="mt-0.5 size-4 shrink-0" /><div>{children}</div>
    </div>
  );
}
