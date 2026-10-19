import { useEffect, useState } from 'react'
import { api } from '../lib/api'
import { Badge, Card, ErrorBox, Loading, PageHeader, SourceLink } from '../components/ui'
import type { CampusOut } from '../lib/types'

export default function Campuses() {
  const [items, setItems] = useState<CampusOut[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  useEffect(() => {
    api
      .campuses()
      .then(setItems)
      .catch((e: Error) => setError(e.message))
      .finally(() => setLoading(false))
  }, [])

  return (
    <div>
      <PageHeader title="Campuses" subtitle="Campus locations listed on KMU pages." />
      {error && <ErrorBox message={error} />}
      {loading ? (
        <Loading label="Loading campuses…" />
      ) : (
        <div className="mt-6 grid gap-4 md:grid-cols-2">
          {items.map((c) => (
            <Card key={c.id}>
              <div className="flex items-start justify-between gap-2">
                <h3 className="font-semibold text-slate-900">{c.name}</h3>
                <Badge status="verified" />
              </div>
              <p className="mt-1 text-sm text-slate-500">
                {c.city ?? '—'} {c.address ? `• ${c.address}` : ''}
              </p>
              <div className="mt-2 text-sm">
                <SourceLink url={c.source_url} title={null} />
              </div>
            </Card>
          ))}
        </div>
      )}
    </div>
  )
}