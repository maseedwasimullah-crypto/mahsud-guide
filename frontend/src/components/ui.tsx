import type { ReactNode } from 'react'

export function PageHeader({ title, subtitle }: { title: string; subtitle?: string }) {
  return (
    <header className="mb-8 border-b border-slate-200 pb-6">
      <h1 className="text-3xl font-bold tracking-tight text-slate-900">{title}</h1>
      {subtitle && <p className="mt-2 max-w-3xl text-slate-600">{subtitle}</p>}
    </header>
  )
}

export function Card({ children, className = '' }: { children: ReactNode; className?: string }) {
  return (
    <div className={`rounded-xl border border-slate-200 bg-white p-5 shadow-sm ${className}`}>{children}</div>
  )
}

export function Badge({ status }: { status: string }) {
  const styles: Record<string, string> = {
    verified: 'bg-emerald-100 text-emerald-800 ring-emerald-200',
    active: 'bg-emerald-100 text-emerald-800 ring-emerald-200',
    open: 'bg-emerald-100 text-emerald-800 ring-emerald-200',
    eligible: 'bg-emerald-100 text-emerald-800 ring-emerald-200',
    closed: 'bg-slate-100 text-slate-600 ring-slate-200',
    pending: 'bg-amber-100 text-amber-800 ring-amber-200',
    superseded: 'bg-amber-100 text-amber-800 ring-amber-200',
    historical: 'bg-amber-100 text-amber-800 ring-amber-200',
    insufficient_information: 'bg-amber-100 text-amber-800 ring-amber-200',
    conflicting: 'bg-red-100 text-red-800 ring-red-200',
    not_eligible: 'bg-red-100 text-red-800 ring-red-200',
    unverified: 'bg-red-100 text-red-800 ring-red-200',
    demo: 'bg-red-100 text-red-800 ring-red-200',
  }
  const label = status.replace(/_/g, ' ')
  return (
    <span
      className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium ring-1 ring-inset ${styles[status] ?? 'bg-sky-100 text-sky-800 ring-sky-200'}`}
    >
      {label}
    </span>
  )
}

export function Loading({ label = 'Loading…' }: { label?: string }) {
  return (
    <div className="flex items-center gap-3 py-10 text-slate-500" role="status">
      <span className="h-4 w-4 animate-spin rounded-full border-2 border-slate-300 border-t-emerald-600" />
      {label}
    </div>
  )
}

export function ErrorBox({ message }: { message: string }) {
  return (
    <div className="rounded-lg border border-red-200 bg-red-50 p-4 text-sm text-red-800" role="alert">
      {message}
    </div>
  )
}

export function EmptyState({ message }: { message: string }) {
  return <p className="py-8 text-center text-slate-500">{message}</p>
}

export function Disclaimer({ children }: { children: ReactNode }) {
  return (
    <p className="rounded-lg border border-amber-200 bg-amber-50 p-3 text-xs leading-relaxed text-amber-900">
      {children}
    </p>
  )
}

export function SourceLink({ url, title }: { url: string | null; title?: string | null }) {
  if (!url) return <span className="text-xs text-slate-400">No source recorded</span>
  return (
    <a
      href={url}
      target="_blank"
      rel="noopener noreferrer"
      className="break-anywhere text-sm font-medium text-emerald-700 hover:text-emerald-900 hover:underline"
    >
      {title || url} ↗
    </a>
  )
}

export function Stat({ label, value }: { label: string; value: number | string }) {
  return (
    <div className="rounded-xl border border-slate-200 bg-white p-4 text-center shadow-sm">
      <div className="text-2xl font-bold text-slate-900">{value}</div>
      <div className="mt-1 text-xs font-medium uppercase tracking-wide text-slate-500">{label}</div>
    </div>
  )
}
