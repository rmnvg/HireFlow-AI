"use client";

import { X } from "lucide-react";
import { useEffect } from "react";

import { Button } from "@/components/ui/button";

export function Dialog({ children, description, onClose, open, title }: { children: React.ReactNode; description?: string; onClose: () => void; open: boolean; title: string }) {
  useEffect(() => {
    if (!open) return;
    const close = (event: KeyboardEvent) => event.key === "Escape" && onClose();
    window.addEventListener("keydown", close);
    return () => window.removeEventListener("keydown", close);
  }, [onClose, open]);

  if (!open) return null;
  return (
    <div aria-modal="true" className="fixed inset-0 z-[60] grid place-items-center p-4" role="dialog">
      <button aria-label="Close dialog" className="absolute inset-0 bg-slate-950/40 backdrop-blur-sm" onClick={onClose} />
      <div className="relative max-h-[90vh] w-full max-w-lg overflow-auto rounded-2xl border bg-white p-6 shadow-2xl">
        <div className="flex items-start justify-between gap-4">
          <div><h2 className="text-lg font-semibold text-slate-950">{title}</h2>{description ? <p className="mt-1 text-sm leading-5 text-slate-500">{description}</p> : null}</div>
          <Button aria-label="Close dialog" onClick={onClose} size="icon" variant="ghost"><X className="size-4" /></Button>
        </div>
        <div className="mt-5">{children}</div>
      </div>
    </div>
  );
}
