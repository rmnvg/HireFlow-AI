import {
  ArrowRight,
  Bell,
  BriefcaseBusiness,
  CalendarDays,
  ChartNoAxesCombined,
  ChevronDown,
  CircleUserRound,
  Clock3,
  LayoutDashboard,
  Plus,
  Search,
  Settings,
  Sparkles,
  Users,
} from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { cn } from "@/lib/utils";

const metrics = [
  { label: "Active roles", value: "12", change: "+2 this month", icon: BriefcaseBusiness },
  { label: "Candidates", value: "248", change: "+18 this week", icon: Users },
  { label: "Interviews", value: "36", change: "8 scheduled today", icon: CalendarDays },
  { label: "Time to hire", value: "18d", change: "3 days faster", icon: Clock3 },
];

const pipeline = [
  { stage: "Applied", count: 124, percent: 100 },
  { stage: "AI screened", count: 82, percent: 66 },
  { stage: "Interview", count: 36, percent: 29 },
  { stage: "Offer", count: 9, percent: 7 },
];

const activity = [
  { initials: "AM", name: "Aisha Mehta", action: "advanced to technical interview", role: "Senior Product Designer", time: "12 min ago" },
  { initials: "RK", name: "Rohan Kapoor", action: "completed AI screening", role: "Backend Engineer", time: "38 min ago" },
  { initials: "NS", name: "Nina Shah", action: "accepted the interview invite", role: "Growth Marketing Lead", time: "1 hr ago" },
];

const navigation = [
  { label: "Overview", icon: LayoutDashboard, active: true },
  { label: "Jobs", icon: BriefcaseBusiness },
  { label: "Candidates", icon: Users },
  { label: "Interviews", icon: CalendarDays },
  { label: "Analytics", icon: ChartNoAxesCombined },
];

export default function Dashboard() {
  return (
    <div className="min-h-screen lg:grid lg:grid-cols-[248px_1fr]">
      <aside className="hidden border-r bg-white lg:flex lg:flex-col">
        <div className="flex h-18 items-center gap-3 border-b px-6">
          <div className="flex size-9 items-center justify-center rounded-xl bg-primary text-primary-foreground shadow-lg shadow-primary/20">
            <Sparkles className="size-5" />
          </div>
          <div>
            <p className="font-bold tracking-tight">HireFlow AI</p>
            <p className="text-xs text-muted-foreground">Hiring workspace</p>
          </div>
        </div>
        <nav className="flex-1 space-y-1 p-4">
          <p className="mb-3 px-3 text-[11px] font-semibold uppercase tracking-[0.15em] text-muted-foreground">Workspace</p>
          {navigation.map(({ label, icon: Icon, active }) => (
            <button
              className={cn(
                "flex w-full items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition-colors",
                active ? "bg-secondary text-secondary-foreground" : "text-muted-foreground hover:bg-muted hover:text-foreground",
              )}
              key={label}
            >
              <Icon className="size-4.5" />
              {label}
            </button>
          ))}
        </nav>
        <div className="border-t p-4">
          <button className="flex w-full items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium text-muted-foreground hover:bg-muted hover:text-foreground">
            <Settings className="size-4.5" /> Settings
          </button>
          <div className="mt-3 flex items-center gap-3 rounded-xl bg-muted p-3">
            <div className="flex size-9 items-center justify-center rounded-full bg-slate-800 text-xs font-semibold text-white">RM</div>
            <div className="min-w-0 flex-1">
              <p className="truncate text-sm font-semibold">Recruiting team</p>
              <p className="truncate text-xs text-muted-foreground">Admin workspace</p>
            </div>
            <ChevronDown className="size-4 text-muted-foreground" />
          </div>
        </div>
      </aside>

      <main className="min-w-0">
        <header className="flex h-18 items-center justify-between border-b bg-white px-5 sm:px-8">
          <div className="flex items-center gap-3 lg:hidden">
            <div className="flex size-9 items-center justify-center rounded-xl bg-primary text-white"><Sparkles className="size-5" /></div>
            <span className="font-bold">HireFlow AI</span>
          </div>
          <div className="relative hidden w-full max-w-sm lg:block">
            <Search className="absolute left-3 top-1/2 size-4 -translate-y-1/2 text-muted-foreground" />
            <input aria-label="Search" className="h-10 w-full rounded-lg border bg-background pl-10 pr-4 text-sm outline-none transition focus:border-primary focus:ring-2 focus:ring-primary/10" placeholder="Search candidates, jobs..." />
          </div>
          <div className="flex items-center gap-2">
            <Button aria-label="Notifications" size="icon" variant="ghost"><Bell className="size-5" /></Button>
            <Button className="hidden sm:inline-flex"><Plus className="size-4" /> Create job</Button>
            <CircleUserRound className="size-8 text-muted-foreground sm:hidden" />
          </div>
        </header>

        <div className="mx-auto max-w-[1500px] space-y-7 p-5 sm:p-8">
          <section className="flex flex-col justify-between gap-4 sm:flex-row sm:items-end">
            <div>
              <p className="mb-1 text-sm font-medium text-primary">Wednesday, September 2</p>
              <h1 className="text-2xl font-bold tracking-tight sm:text-3xl">Good morning, recruiting team</h1>
              <p className="mt-1 text-sm text-muted-foreground">Here&apos;s what&apos;s happening across your hiring pipeline.</p>
            </div>
            <Button variant="outline"><ChartNoAxesCombined className="size-4" /> View reports</Button>
          </section>

          <section className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
            {metrics.map(({ label, value, change, icon: Icon }) => (
              <Card key={label}>
                <CardContent className="p-5">
                  <div className="flex items-start justify-between">
                    <div>
                      <p className="text-sm font-medium text-muted-foreground">{label}</p>
                      <p className="mt-2 text-3xl font-bold tracking-tight">{value}</p>
                    </div>
                    <div className="flex size-10 items-center justify-center rounded-xl bg-secondary text-secondary-foreground"><Icon className="size-5" /></div>
                  </div>
                  <p className="mt-4 text-xs font-medium text-emerald-600">{change}</p>
                </CardContent>
              </Card>
            ))}
          </section>

          <section className="grid gap-6 xl:grid-cols-[1.15fr_0.85fr]">
            <Card>
              <CardHeader className="flex-row items-start justify-between space-y-0">
                <div><CardTitle>Hiring pipeline</CardTitle><CardDescription className="mt-1.5">Candidates across all active roles</CardDescription></div>
                <Badge>Last 30 days</Badge>
              </CardHeader>
              <CardContent className="space-y-5">
                {pipeline.map((item) => (
                  <div key={item.stage}>
                    <div className="mb-2 flex items-center justify-between text-sm"><span className="font-medium">{item.stage}</span><span className="font-semibold">{item.count}</span></div>
                    <div className="h-2.5 overflow-hidden rounded-full bg-muted"><div className="h-full rounded-full bg-primary" style={{ width: `${item.percent}%` }} /></div>
                  </div>
                ))}
              </CardContent>
            </Card>

            <Card>
              <CardHeader className="flex-row items-start justify-between space-y-0">
                <div><CardTitle>AI recommendations</CardTitle><CardDescription className="mt-1.5">High-impact actions for your team</CardDescription></div>
                <div className="flex size-9 items-center justify-center rounded-lg bg-secondary text-secondary-foreground"><Sparkles className="size-4.5" /></div>
              </CardHeader>
              <CardContent className="space-y-3">
                <div className="rounded-xl border bg-gradient-to-br from-white to-secondary/35 p-4">
                  <Badge className="mb-3 bg-amber-100 text-amber-700">Needs attention</Badge>
                  <p className="font-semibold">6 candidates are waiting for feedback</p>
                  <p className="mt-1 text-sm leading-6 text-muted-foreground">Review interview notes to keep your strongest candidates engaged.</p>
                  <button className="mt-3 flex items-center gap-1 text-sm font-semibold text-primary">Review candidates <ArrowRight className="size-4" /></button>
                </div>
                <div className="rounded-xl border p-4">
                  <p className="font-semibold">Backend Engineer pipeline is strong</p>
                  <p className="mt-1 text-sm leading-6 text-muted-foreground">AI screening identified 8 high-match candidates this week.</p>
                </div>
              </CardContent>
            </Card>
          </section>

          <Card>
            <CardHeader className="flex-row items-center justify-between space-y-0">
              <div><CardTitle>Recent activity</CardTitle><CardDescription className="mt-1.5">Latest candidate and team updates</CardDescription></div>
              <Button size="sm" variant="ghost">View all <ArrowRight className="size-4" /></Button>
            </CardHeader>
            <CardContent>
              <div className="divide-y">
                {activity.map((item) => (
                  <div className="flex items-center gap-4 py-4 first:pt-0 last:pb-0" key={item.name}>
                    <div className="flex size-10 shrink-0 items-center justify-center rounded-full bg-slate-100 text-xs font-bold text-slate-700">{item.initials}</div>
                    <div className="min-w-0 flex-1">
                      <p className="truncate text-sm"><span className="font-semibold">{item.name}</span> <span className="text-muted-foreground">{item.action}</span></p>
                      <p className="mt-1 text-xs text-muted-foreground">{item.role}</p>
                    </div>
                    <span className="hidden shrink-0 text-xs text-muted-foreground sm:block">{item.time}</span>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        </div>
      </main>
    </div>
  );
}
