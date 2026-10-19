import { useEffect, useState } from 'react'
import { api } from '../lib/api'
import { Badge, Card, ErrorBox, Loading, PageHeader, SourceLink } from '../components/ui'
import type { InstitutionOut } from '../lib/types'

export default function Institutions() {
  const [items, setItems] = useState<InstitutionOut[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [q, setQ] = useState('')
  const [type, setType] = useState('')
  const [city, setCity] = useState('')

  useEffect(() => {
    void load()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [q, type, city])

  const load = async () => {
    setLoading(true)
    setError('')
    try {
      const res = await api.institutions({ q: q || undefined, type: type || undefined, city: city || undefined })
      setItems(res.items)
    } catch (e) {
      if (e instanceof Error) setError(e.message)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div>
      <PageHeader title="Institutes" subtitle="Constituent institutes and affiliated colleges." />
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
            placeholder="Search institutes..."
            className="w-full rounded-lg border border-slate-300 px-3 py-2 shadow-sm outline-none focus:border-emerald-500 focus:ring-2 focus:ring-emerald-200 md:w-72"
          />
          <select
            value={type}
            onChange={(e) => setType(e.target.value)}
            className="rounded-lg border border-slate-300 px-3 py-2 shadow-sm outline-none focus:border-emerald-500 focus:ring-2 focus:ring-emerald-200"
          >
            <option value="">All types</option>
            <option value="constituent_institute">Constituent Institute</option>
            <option value="affiliated_college">Affiliated College</option>
          </select>
          <input
            value={city}
            onChange={(e) => setCity(e.target.value)}
            placeholder="City"
            className="rounded-lg border border-slate-300 px-3 py-2 shadow-sm outline-none focus:border-emerald-500 focus:ring-2 focus:ring-emerald-200 md:w-40"
          />
          <button
            type="submit"
            className="rounded-lg bg-emerald-700 px-4 py-2 font-semibold text-white shadow-sm hover:bg-emerald-800"
          >
            Filter
          </button>
        </form>
      </Card>
      {loading ? (
        <Loading label="Loading institutions…" />
      ) : (
        <div className="mt-6 grid gap-4 md:grid-cols-2">
          {items.map((i) => (
            <Card key={i.id}>
              <div className="flex items-start justify-between gap-2">
                <h3 className="font-semibold text-slate-900">{i.name}</h3>
                <Badge status={i.verification_status} />
              </div>
              <p className="mt-1 text-sm text-slate-500">
                {i.institution_type.replace('_', ' ')} • {i.city ?? '—'}
              </p>
              <div className="mt-2 text-sm">
                <SourceLink url={i.source_url} title={null} />
              </div>
            </Card>
          ))}
        </div>
      )}
    </div>
  )
}