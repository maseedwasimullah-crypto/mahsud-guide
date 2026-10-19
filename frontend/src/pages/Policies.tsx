import { useEffect, useState } from 'react'
import { api } from '../lib/api'
import { Badge, Card, ErrorBox, Loading, PageHeader, SourceLink } from '../components/ui'
import type { PolicyOut } from '../lib/types'

export default function Policies() {
  const [items, setItems] = useState<PolicyOut[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  useEffect(() => {
    api
      .policies()
      .then(setItems)
      .catch((e: Error) => setError(e.message))
      .finally(() => setLoading(false))
  }, [])

  return (
    <div>
      <PageHeader title="Policies" subtitle="Policies with source links and verification status." />
      {error && <ErrorBox message={error} />}
      {loading ? (
        <Loading label="Loading policies…" />
      ) : (
        <div className="mt-6 space-y-4">
          {items.map((p) => (
            <Card key={p.id}>
              <div className="flex items-start justify-between gap-2">
                <h3 className="font-semibold text-slate-900">{p.title}</h3>
                <Badge status={p.verification_status} />
              </div>
              {p.category && <p className="mt-1 text-sm text-slate-500">{p.category}</p>}
              {p.summary && <p className="mt-2 text-sm text-slate-700">{p.summary}</p>}
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