export function PageHeader({ actions, description, eyebrow, title }: { actions?: React.ReactNode; description: string; eyebrow?: string; title: string }) {
  return (
    <div className="mb-7 flex flex-col justify-between gap-4 sm:flex-row sm:items-end">
      <div>
        {eyebrow ? <p className="mb-1 text-xs font-semibold uppercase tracking-[0.14em] text-violet-600">{eyebrow}</p> : null}
        <h1 className="text-2xl font-bold tracking-tight text-slate-950 sm:text-3xl">{title}</h1>
        <p className="mt-1.5 max-w-2xl text-sm leading-6 text-slate-500">{description}</p>
      </div>
      {actions ? <div className="flex shrink-0 gap-2">{actions}</div> : null}
    </div>
  );
}
