import type { LucideIcon } from "lucide-react";

export function EmptyState({ action, description, icon: Icon, title }: { action?: React.ReactNode; description: string; icon: LucideIcon; title: string }) {
  return (
    <div className="flex min-h-64 flex-col items-center justify-center px-6 py-12 text-center">
      <div className="flex size-12 items-center justify-center rounded-2xl bg-violet-50 text-violet-600"><Icon className="size-6" /></div>
      <h3 className="mt-4 font-semibold text-slate-900">{title}</h3>
      <p className="mt-1 max-w-sm text-sm leading-6 text-slate-500">{description}</p>
      {action ? <div className="mt-5">{action}</div> : null}
    </div>
  );
}
