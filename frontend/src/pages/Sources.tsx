import { useEffect, useState } from 'react'
import { api } from '../lib/api'
import { Badge, Card, ErrorBox, Loading, PageHeader, SourceLink } from '../components/ui'
import type { Source } from '../lib/types'

export default function Sources() {
  const [items, setItems] = useState<Source[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [q, setQ] = useState('')

  useEffect(() => {
    void load()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [q])

  const load = async () => {
    setLoading(true)
    setError('')
    try {
      const res = await api.sources(q || undefined)
      setItems(res)
    } catch (e) {
      if (e instanceof Error) setError(e.message)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div>
      <PageHeader
        title="Sources"
        subtitle="All official sources tracked by the system with verification status."
      />
      {error && <ErrorBox message={error} />}
      <Card>
        <form
          onSubmit={(e) => {
            e.preventDefault()
            load()
          }}
          className="flex gap-3"
        >
          <input
            value={q}
            onChange={(e) => setQ(e.target.value)}
            placeholder="Search sources..."
            className="w-full rounded-lg border border-slate-300 px-3 py-2 shadow-sm outline-none focus:border-emerald-500 focus:ring-2 focus:ring-emerald-200 md:w-72"
          />
          <button
            type="submit"
            className="rounded-lg bg-emerald-700 px-4 py-2 font-semibold text-white shadow-sm hover:bg-emerald-800"
          >
            Search
          </button>
        </form>
      </Card>
      {loading ? (
        <Loading label="Loading sources…" />
      ) : (
        <div className="mt-6 overflow-x-auto">
          <table className="min-w-full divide-y divide-slate-200">
            <thead>
              <tr className="text-left text-xs font-medium uppercase tracking-wide text-slate-500">
                <th className="px-3 py-2">Name</th>
                <th className="px-3 py-2">Institution</th>
                <th className="px-3 py-2">Category</th>
                <th className="px-3 py-2">Official</th>
                <th className="px-3 py-2">Verification</th>
                <th className="px-3 py-2">URL</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 bg-white text-sm text-slate-700">
              {items.map((s) => (
                <tr key={s.id}>
                  <td className="px-3 py-2 font-medium text-slate-900">{s.name}</td>
                  <td className="px-3 py-2">{s.institution ?? '—'}</td>
                  <td className="px-3 py-2">{s.category ?? '—'}</td>
                  <td className="px-3 py-2">{s.is_official ? 'Yes' : 'No'}</td>
                  <td className="px-3 py-2">
                    <Badge status={s.verification_status} />
                  </td>
                  <td className="px-3 py-2 max-w-xs">
                    <SourceLink url={s.url} title={s.url} />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}