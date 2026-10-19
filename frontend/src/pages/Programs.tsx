import { useEffect, useState } from 'react'
import { api } from '../lib/api'
import { Badge, Card, ErrorBox, Loading, PageHeader, SourceLink } from '../components/ui'
import type { ProgramOut } from '../lib/types'

export default function Programs() {
  const [items, setItems] = useState<ProgramOut[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [q, setQ] = useState('')
  const [level, setLevel] = useState('')

  useEffect(() => {
    void load()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [q, level])

  const load = async () => {
    setLoading(true)
    setError('')
    try {
      const res = await api.programs({ q: q || undefined, degree_level: level || undefined })
      setItems(res.items)
    } catch (e) {
      if (e instanceof Error) setError(e.message)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div>
      <PageHeader title="Programs" subtitle="Degree programs listed in KMU catalog." />
      {error && <ErrorBox message={error} />}
      <Card>
        <form
          onSubmit={(e) => {
            e.preventDefault()
            load()
          }}
          className="flex flex-wrap gap-3"
        >
          <input
            value={q}
            onChange={(e) => setQ(e.target.value)}
            placeholder="Search programs..."
            className="w-full rounded-lg border border-slate-300 px-3 py-2 shadow-sm outline-none focus:border-emerald-500 focus:ring-2 focus:ring-emerald-200 md:w-72"
          />
          <select
            value={level}
            onChange={(e) => setLevel(e.target.value)}
            className="rounded-lg border border-slate-300 px-3 py-2 shadow-sm outline-none focus:border-emerald-500 focus:ring-2 focus:ring-emerald-200"
          >
            <option value="">All levels</option>
            <option value="undergraduate">Undergraduate</option>
            <option value="postgraduate">Postgraduate</option>
            <option value="diploma">Diploma</option>
          </select>
          <button
            type="submit"
            className="rounded-lg bg-emerald-700 px-4 py-2 font-semibold text-white shadow-sm hover:bg-emerald-800"
          >
            Filter
          </button>
        </form>
      </Card>
      {loading ? (
        <Loading label="Loading programs…" />
      ) : (
        <div className="mt-6 grid gap-4 md:grid-cols-2">
          {items.map((p) => (
            <Card key={p.id}>
              <div className="flex items-start justify-between gap-2">
                <h3 className="font-semibold text-slate-900">{p.title}</h3>
                <Badge status={p.verification_status} />
              </div>
              <p className="mt-1 text-sm text-slate-500">
                {p.degree_level} • {p.department ?? '—'} • {p.duration ?? '—'}
              </p>
              <div className="mt-2 text-sm">
                <SourceLink url={p.source_url} title={null} />
              </div>
            </Card>
          ))}
        </div>
      )}
    </div>
  )
}