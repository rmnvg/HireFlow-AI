import { ArrowDown, Bot, CalendarCheck2, Database, Fingerprint, Server, ShieldCheck, Smartphone, Users } from "lucide-react";

import { PageHeader } from "@/components/page-header";
import { Alert } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

const layers = [
  { icon: Smartphone, title: "Employee experience", detail: "Responsive web/PWA check-in, shift view and leave requests" },
  { icon: Server, title: "Attendance API", detail: "FastAPI validation, policy engine and manager workflows" },
  { icon: Fingerprint, title: "Verification layer", detail: "Device registration, geofence checks and optional biometric provider" },
  { icon: Database, title: "System of record", detail: "PostgreSQL events, shifts, policies and immutable audit history" },
];

export default function AttendancePage() {
  return (
    <div>
      <PageHeader description="A production-minded design for adding workforce attendance without coupling it to the recruiting domain." eyebrow="Assignment 3" title="Attendance architecture proposal" />
      <Alert><strong>Recommendation:</strong> ship attendance as a bounded module with its own authorization and audit model, while reusing the existing frontend, API deployment pattern and PostgreSQL platform.</Alert>

      <div className="mt-6 grid gap-6 xl:grid-cols-[1.05fr_0.95fr]">
        <Card className="border-slate-200 shadow-sm">
          <CardHeader><div className="flex items-center justify-between"><CardTitle>Reference architecture</CardTitle><Badge>Event-led</Badge></div></CardHeader>
          <CardContent>
            <div className="mx-auto max-w-xl space-y-3">
              {layers.map(({ detail, icon: Icon, title }, index) => (
                <div key={title}>
                  <div className="flex items-center gap-4 rounded-2xl border border-slate-200 bg-white p-4 shadow-sm"><span className="flex size-11 shrink-0 items-center justify-center rounded-xl bg-violet-50 text-violet-600"><Icon className="size-5" /></span><div><p className="font-semibold text-slate-900">{title}</p><p className="mt-0.5 text-sm leading-5 text-slate-500">{detail}</p></div></div>
                  {index < layers.length - 1 ? <ArrowDown className="mx-auto my-2 size-5 text-slate-300" /> : null}
                </div>
              ))}
            </div>
          </CardContent>
        </Card>

        <div className="space-y-6">
          <ProposalCard icon={CalendarCheck2} title="Core domain model"><ul><li>Employees, teams and reporting hierarchy</li><li>Shift templates, rosters and holiday calendars</li><li>Immutable check-in/check-out events</li><li>Daily attendance summaries and exception requests</li></ul></ProposalCard>
          <ProposalCard icon={ShieldCheck} title="Controls and trust"><ul><li>Role-based employee, manager and HR permissions</li><li>Server-side timestamps and configurable geofences</li><li>Append-only audit events for every correction</li><li>Encrypted provider data with configurable retention</li></ul></ProposalCard>
          <ProposalCard icon={Bot} title="Automation"><ul><li>Queue-backed daily summary calculation</li><li>Missed check-out and late-arrival notifications</li><li>Manager approval workflow for corrections</li><li>Payroll export through versioned integrations</li></ul></ProposalCard>
        </div>
      </div>

      <Card className="mt-6 border-slate-200 shadow-sm">
        <CardHeader><CardTitle>Delivery sequence</CardTitle></CardHeader>
        <CardContent><div className="grid gap-4 md:grid-cols-3"><Phase number="01" title="Foundation" text="Employee sync, shifts, web check-in and immutable attendance events." /><Phase number="02" title="Operations" text="Manager exceptions, approvals, reporting and scheduled notifications." /><Phase number="03" title="Scale" text="Mobile PWA, optional device/biometric verification and payroll exports." /></div></CardContent>
      </Card>
    </div>
  );
}

function ProposalCard({ children, icon: Icon, title }: { children: React.ReactNode; icon: typeof Users; title: string }) {
  return <Card className="border-slate-200 shadow-sm"><CardHeader className="pb-3"><CardTitle className="flex items-center gap-2 text-base"><Icon className="size-5 text-violet-600" />{title}</CardTitle></CardHeader><CardContent><div className="text-sm leading-7 text-slate-600 [&_li]:ml-5 [&_li]:list-disc">{children}</div></CardContent></Card>;
}

function Phase({ number, text, title }: { number: string; text: string; title: string }) {
  return <div className="rounded-xl border border-slate-200 bg-slate-50 p-4"><span className="text-xs font-bold text-violet-600">PHASE {number}</span><p className="mt-2 font-semibold text-slate-900">{title}</p><p className="mt-1 text-sm leading-6 text-slate-500">{text}</p></div>;
}
