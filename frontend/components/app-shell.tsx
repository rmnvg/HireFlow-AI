"use client";

import {
  Bell,
  BriefcaseBusiness,
  CalendarCheck2,
  Headphones,
  LayoutDashboard,
  Menu,
  Plus,
  Sparkles,
  Users,
  X,
} from "lucide-react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useState } from "react";

import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

const navigation = [
  { href: "/", label: "Dashboard", icon: LayoutDashboard },
  { href: "/jobs/new", label: "New job", icon: BriefcaseBusiness },
  { href: "/candidates", label: "Candidates", icon: Users },
  { href: "/calls", label: "AI calls", icon: Headphones },
  { href: "/attendance", label: "Attendance", icon: CalendarCheck2 },
];

export function AppShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const [open, setOpen] = useState(false);

  const nav = (
    <nav className="space-y-1">
      <p className="mb-3 px-3 text-[11px] font-semibold uppercase tracking-[0.16em] text-slate-400">
        Recruiting workspace
      </p>
      {navigation.map(({ href, label, icon: Icon }) => {
        const active = href === "/" ? pathname === href : pathname.startsWith(href);
        return (
          <Link
            className={cn(
              "flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm font-medium transition",
              active
                ? "bg-violet-50 text-violet-700 shadow-sm"
                : "text-slate-500 hover:bg-slate-50 hover:text-slate-900",
            )}
            href={href}
            key={href}
            onClick={() => setOpen(false)}
          >
            <Icon className="size-[18px]" />
            {label}
          </Link>
        );
      })}
    </nav>
  );

  return (
    <div className="min-h-screen bg-slate-50 lg:grid lg:grid-cols-[248px_1fr]">
      <aside className="hidden border-r border-slate-200 bg-white lg:flex lg:flex-col">
        <Brand />
        <div className="flex-1 p-4">{nav}</div>
        <div className="border-t border-slate-100 p-4">
          <div className="rounded-xl bg-slate-50 p-3">
            <p className="text-sm font-semibold text-slate-800">Recruiting team</p>
            <p className="mt-0.5 text-xs text-slate-500">AI-assisted workspace</p>
          </div>
        </div>
      </aside>

      {open ? (
        <div className="fixed inset-0 z-50 lg:hidden">
          <button aria-label="Close navigation" className="absolute inset-0 bg-slate-950/30 backdrop-blur-sm" onClick={() => setOpen(false)} />
          <aside className="relative h-full w-[280px] bg-white shadow-2xl">
            <div className="flex items-center justify-between border-b pr-3">
              <Brand />
              <Button aria-label="Close navigation" onClick={() => setOpen(false)} size="icon" variant="ghost"><X className="size-5" /></Button>
            </div>
            <div className="p-4">{nav}</div>
          </aside>
        </div>
      ) : null}

      <div className="min-w-0">
        <header className="sticky top-0 z-30 flex h-[72px] items-center justify-between border-b border-slate-200/80 bg-white/90 px-4 backdrop-blur sm:px-7">
          <div className="flex items-center gap-3">
            <Button aria-label="Open navigation" className="lg:hidden" onClick={() => setOpen(true)} size="icon" variant="ghost"><Menu className="size-5" /></Button>
            <div>
              <p className="text-sm font-semibold text-slate-900">HireFlow AI</p>
              <p className="hidden text-xs text-slate-500 sm:block">Recruiting command center</p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <Button aria-label="Notifications" size="icon" variant="ghost"><Bell className="size-5" /></Button>
            <Button asChild className="hidden sm:inline-flex"><Link href="/jobs/new"><Plus className="size-4" /> New job</Link></Button>
          </div>
        </header>
        <main className="mx-auto w-full max-w-[1600px] p-4 sm:p-7 lg:p-8">{children}</main>
      </div>
    </div>
  );
}

function Brand() {
  return (
    <Link className="flex h-[72px] items-center gap-3 px-6" href="/">
      <span className="flex size-9 items-center justify-center rounded-xl bg-violet-600 text-white shadow-lg shadow-violet-200"><Sparkles className="size-5" /></span>
      <span>
        <span className="block font-bold tracking-tight text-slate-950">HireFlow AI</span>
        <span className="block text-[11px] text-slate-500">Recruit smarter</span>
      </span>
    </Link>
  );
}
