import type { LucideIcon } from "lucide-react";
import {
  ArrowDown,
  ArrowRight,
  BadgeCheck,
  Bot,
  BrainCircuit,
  Building2,
  Calculator,
  CheckCircle2,
  CircleUserRound,
  Clock3,
  CreditCard,
  Database,
  Fingerprint,
  HardDrive,
  KeyRound,
  LockKeyhole,
  Network,
  Phone,
  Scale,
  Server,
  ShieldCheck,
  UserCheck,
  Users,
  WifiOff,
} from "lucide-react";

import { PageHeader } from "@/components/page-header";
import { Alert } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

const normalFlow = [
  { icon: CreditCard, title: "Identify", text: "Tap RFID card at the office kiosk." },
  { icon: KeyRound, title: "Verify", text: "Enter a PIN or use the biometric reader." },
  { icon: HardDrive, title: "Queue locally", text: "Create a signed, timestamped edge event." },
  { icon: Database, title: "Synchronize", text: "Central backend validates and stores the event." },
  { icon: CheckCircle2, title: "Calculate", text: "Rules engine updates the attendance record." },
];

const outageFlow = [
  { icon: WifiOff, title: "Detect outage", text: "Kiosk continues without central connectivity." },
  { icon: HardDrive, title: "Persist safely", text: "Encrypted events remain in the local edge queue." },
  { icon: Network, title: "Reconnect", text: "Queue resumes with ordered, idempotent delivery." },
  { icon: BadgeCheck, title: "Reconcile", text: "Backend deduplicates and records original event time." },
];

const voiceFlow = [
  { icon: Phone, title: "Call office line", text: "Employee uses the registered location landline." },
  { icon: Bot, title: "Hunar verifies", text: "Voice agent collects identity, PIN and attendance intent." },
  { icon: UserCheck, title: "Route exception", text: "Manager reviews the exceptional attendance request." },
  { icon: Database, title: "Record decision", text: "Approval or rejection enters the immutable audit trail." },
];

export default function AttendancePage() {
  return (
    <div>
      <PageHeader
        description="A resilient, auditable attendance design for a distributed workforce where personal smartphones cannot be assumed."
        eyebrow="Assignment 3 · Architecture proposal"
        title="Attendance at Scale Without Smartphones"
      />

      <Alert>
        <strong>Design boundary:</strong> this page is an architecture proposal only. It does
        not introduce attendance APIs, database tables or production workflows into HireFlow.
      </Alert>

      <SectionCard icon={Building2} number="1" title="Problem">
        <div className="grid gap-5 lg:grid-cols-[1.3fr_0.7fr]">
          <div className="space-y-3 text-sm leading-7 text-slate-600">
            <p>
              One thousand employees work across 100 offices with uneven connectivity and no
              guarantee that every employee owns, carries or can use a smartphone at work.
              Attendance must remain available during network outages while preventing buddy
              punching, location spoofing and silent record changes.
            </p>
            <p>
              The solution therefore needs trusted shared hardware at each office, an offline
              path, a controlled exception path and one central source of truth for payroll and HR.
            </p>
          </div>
          <div className="grid grid-cols-2 gap-3">
            <Stat value="1,000" label="Employees" />
            <Stat value="100" label="Offices" />
            <Stat value="Offline" label="Capable" />
            <Stat value="Audited" label="End to end" />
          </div>
        </div>
      </SectionCard>

      <SectionCard icon={Network} number="2" title="Proposed architecture">
        <div className="rounded-2xl border border-slate-200 bg-slate-50/70 p-4 sm:p-6">
          <div className="grid items-stretch gap-3 lg:grid-cols-[1fr_auto_1fr_auto_1fr]">
            <ArchitectureNode
              icon={Fingerprint}
              eyebrow="100 locations"
              title="RFID kiosk"
              text="RFID card plus employee PIN or biometric verification."
            />
            <FlowArrow />
            <ArchitectureNode
              icon={HardDrive}
              eyebrow="Every office"
              title="Local edge queue"
              text="Encrypted durable queue keeps check-ins available offline."
              tone="amber"
            />
            <FlowArrow />
            <ArchitectureNode
              icon={Server}
              eyebrow="Source of truth"
              title="Central backend"
              text="Validates events, applies policy and writes the audit history."
              tone="emerald"
            />
          </div>

          <div className="mx-auto my-3 flex max-w-xs justify-center">
            <ArrowDown className="size-5 text-slate-300" />
          </div>

          <div className="grid gap-3 lg:grid-cols-3">
            <ArchitectureNode
              icon={Phone}
              eyebrow="Fallback channel"
              title="Registered landline + Hunar"
              text="Accepts voice attendance only from a known office number."
              tone="blue"
            />
            <ArchitectureNode
              icon={UserCheck}
              eyebrow="Human control"
              title="Manager approval"
              text="Reviews voice and other exceptional attendance events."
              tone="violet"
            />
            <ArchitectureNode
              icon={LockKeyhole}
              eyebrow="Accountability"
              title="Immutable audit trail"
              text="Preserves submission, verification, decision and correction history."
              tone="slate"
            />
          </div>
        </div>
      </SectionCard>

      <SectionCard icon={CreditCard} number="3" title="Normal check-in flow">
        <FlowSequence steps={normalFlow} />
      </SectionCard>

      <SectionCard icon={WifiOff} number="4" title="Network outage flow">
        <FlowSequence steps={outageFlow} />
        <Callout>
          The kiosk displays a local receipt immediately. Original device timestamps and monotonic
          sequence numbers are retained; reconnecting never changes when the employee checked in.
        </Callout>
      </SectionCard>

      <SectionCard icon={Phone} number="5" title="Voice fallback flow">
        <FlowSequence steps={voiceFlow} />
        <Callout>
          Caller ID from the registered office landline is a location signal, not sufficient proof
          by itself. The voice request remains exceptional until manager approval.
        </Callout>
      </SectionCard>

      <div className="grid gap-6 xl:grid-cols-2">
        <SectionCard icon={ShieldCheck} number="6" title="Fraud prevention" compact>
          <BulletList
            items={[
              "Bind every RFID card to one active employee and require a second factor.",
              "Use liveness-capable biometric readers where policy and consent allow.",
              "Sign kiosk events with device credentials and rotate keys centrally.",
              "Allow voice fallback only from registered office landlines.",
              "Flag duplicate, impossible or unusual check-in patterns for review.",
              "Require manager approval for exceptions; never overwrite the original event.",
            ]}
          />
        </SectionCard>

        <SectionCard icon={Scale} number="7" title="LLM versus deterministic-code responsibilities" compact>
          <div className="grid gap-4 sm:grid-cols-2">
            <Responsibility
              icon={BrainCircuit}
              label="LLM assists"
              items={[
                "Natural-language daily summaries",
                "Anomaly explanations for reviewers",
                "HR questions over authorized data",
                "Readable management reports",
              ]}
              tone="violet"
            />
            <Responsibility
              icon={Calculator}
              label="Code decides"
              items={[
                "Final present, late or absent status",
                "Shift, grace-period and overtime rules",
                "Deduplication and event ordering",
                "Payroll-ready attendance totals",
              ]}
              tone="emerald"
            />
          </div>
          <p className="mt-4 rounded-xl bg-slate-900 px-4 py-3 text-sm leading-6 text-white">
            The LLM may explain a result, but deterministic, versioned rules always calculate it.
          </p>
        </SectionCard>

        <SectionCard icon={Users} number="8" title="Scaling for 1,000 employees across 100 offices" compact>
          <BulletList
            items={[
              "Provision one independently identifiable edge device per office, with a spare-device process.",
              "Partition inbound events by office and preserve ordering within each device stream.",
              "Use idempotency keys so reconnects and retries cannot double-count attendance.",
              "Process check-ins asynchronously while keeping central reads strongly consistent.",
              "Monitor queue depth, last synchronization, device health and clock drift per location.",
              "Keep stateless backend instances horizontally scalable behind a load balancer.",
            ]}
          />
        </SectionCard>

        <SectionCard icon={CircleUserRound} number="9" title="Privacy and employee consent" compact>
          <BulletList
            items={[
              "Offer PIN as a non-biometric alternative wherever legally or operationally required.",
              "Collect explicit, informed consent before biometric enrollment.",
              "Store biometric templates—not raw images—and isolate them from attendance records.",
              "Limit HR, manager and operator access by role and office scope.",
              "Publish retention periods, correction rights and the purpose of every data field.",
              "Never use attendance data or LLM outputs for undisclosed employee monitoring.",
            ]}
          />
        </SectionCard>
      </div>
    </div>
  );
}

function SectionCard({
  children,
  compact = false,
  icon: Icon,
  number,
  title,
}: {
  children: React.ReactNode;
  compact?: boolean;
  icon: LucideIcon;
  number: string;
  title: string;
}) {
  return (
    <Card className={`${compact ? "" : "mt-6"} border-slate-200 shadow-sm`}>
      <CardHeader className="border-b border-slate-100 pb-4">
        <div className="flex items-center gap-3">
          <span className="flex size-9 items-center justify-center rounded-xl bg-violet-50 text-violet-600">
            <Icon className="size-[18px]" />
          </span>
          <div className="flex items-center gap-2">
            <Badge className="bg-slate-100 text-slate-600">{number}</Badge>
            <CardTitle className="text-lg">{title}</CardTitle>
          </div>
        </div>
      </CardHeader>
      <CardContent className="pt-6">{children}</CardContent>
    </Card>
  );
}

function ArchitectureNode({
  eyebrow,
  icon: Icon,
  text,
  title,
  tone = "violet",
}: {
  eyebrow: string;
  icon: LucideIcon;
  text: string;
  title: string;
  tone?: "amber" | "blue" | "emerald" | "slate" | "violet";
}) {
  const tones = {
    amber: "bg-amber-50 text-amber-700",
    blue: "bg-blue-50 text-blue-700",
    emerald: "bg-emerald-50 text-emerald-700",
    slate: "bg-slate-100 text-slate-700",
    violet: "bg-violet-50 text-violet-700",
  };
  return (
    <div className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
      <div className={`flex size-10 items-center justify-center rounded-xl ${tones[tone]}`}>
        <Icon className="size-5" />
      </div>
      <p className="mt-4 text-[11px] font-bold uppercase tracking-[0.14em] text-slate-400">{eyebrow}</p>
      <h3 className="mt-1 font-semibold text-slate-900">{title}</h3>
      <p className="mt-1 text-sm leading-5 text-slate-500">{text}</p>
    </div>
  );
}

function FlowArrow() {
  return (
    <div className="flex items-center justify-center text-slate-300">
      <ArrowRight className="hidden size-5 lg:block" />
      <ArrowDown className="size-5 lg:hidden" />
    </div>
  );
}

function FlowSequence({ steps }: { steps: Array<{ icon: LucideIcon; text: string; title: string }> }) {
  return (
    <div className="grid gap-2 md:grid-flow-col md:auto-cols-fr">
      {steps.map(({ icon: Icon, text, title }, index) => (
        <div className="contents" key={title}>
          <div className="rounded-xl border border-slate-200 bg-slate-50 p-4">
            <div className="flex items-center gap-2">
              <span className="flex size-8 items-center justify-center rounded-lg bg-white text-violet-600 shadow-sm">
                <Icon className="size-4" />
              </span>
              <span className="text-xs font-bold text-slate-400">{String(index + 1).padStart(2, "0")}</span>
            </div>
            <p className="mt-3 font-semibold text-slate-900">{title}</p>
            <p className="mt-1 text-sm leading-5 text-slate-500">{text}</p>
          </div>
          {index < steps.length - 1 ? (
            <div className="flex items-center justify-center text-slate-300">
              <ArrowRight className="hidden size-4 md:block" />
              <ArrowDown className="size-4 md:hidden" />
            </div>
          ) : null}
        </div>
      ))}
    </div>
  );
}

function Responsibility({
  icon: Icon,
  items,
  label,
  tone,
}: {
  icon: LucideIcon;
  items: string[];
  label: string;
  tone: "emerald" | "violet";
}) {
  return (
    <div className={`rounded-xl border p-4 ${tone === "violet" ? "border-violet-200 bg-violet-50/60" : "border-emerald-200 bg-emerald-50/60"}`}>
      <div className="flex items-center gap-2 font-semibold text-slate-900">
        <Icon className={`size-5 ${tone === "violet" ? "text-violet-600" : "text-emerald-600"}`} />
        {label}
      </div>
      <ul className="mt-3 space-y-2 text-sm leading-5 text-slate-600">
        {items.map((item) => <li className="flex gap-2" key={item}><span aria-hidden="true">•</span><span>{item}</span></li>)}
      </ul>
    </div>
  );
}

function BulletList({ items }: { items: string[] }) {
  return (
    <ul className="grid gap-3 text-sm leading-6 text-slate-600 sm:grid-cols-2">
      {items.map((item) => (
        <li className="flex gap-2.5" key={item}>
          <CheckCircle2 className="mt-1 size-4 shrink-0 text-emerald-500" />
          <span>{item}</span>
        </li>
      ))}
    </ul>
  );
}

function Callout({ children }: { children: React.ReactNode }) {
  return (
    <div className="mt-4 flex gap-3 rounded-xl border border-blue-100 bg-blue-50 px-4 py-3 text-sm leading-6 text-blue-800">
      <Clock3 className="mt-1 size-4 shrink-0" />
      <p>{children}</p>
    </div>
  );
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-xl border border-slate-200 bg-slate-50 p-3 text-center">
      <p className="text-xl font-bold text-slate-900">{value}</p>
      <p className="mt-0.5 text-xs text-slate-500">{label}</p>
    </div>
  );
}
