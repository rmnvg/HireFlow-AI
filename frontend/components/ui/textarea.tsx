import * as React from "react";

import { cn } from "@/lib/utils";

export const Textarea = React.forwardRef<HTMLTextAreaElement, React.TextareaHTMLAttributes<HTMLTextAreaElement>>(
  ({ className, ...props }, ref) => (
    <textarea className={cn("flex min-h-28 w-full rounded-lg border border-slate-200 bg-white px-3 py-2.5 text-sm leading-6 outline-none transition placeholder:text-slate-400 focus:border-violet-500 focus:ring-2 focus:ring-violet-100 disabled:cursor-not-allowed disabled:bg-slate-50 disabled:opacity-70", className)} ref={ref} {...props} />
  ),
);
Textarea.displayName = "Textarea";
