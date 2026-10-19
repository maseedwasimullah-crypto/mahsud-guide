import { useEffect, useState } from 'react'
import { api } from '../lib/api'
import { Badge, Card, ErrorBox, Loading, PageHeader, SourceLink } from '../components/ui'
import type { AdmissionCycleOut, AdmissionRuleOut } from '../lib/types'

export default function Admissions() {
  const [cycles, setCycles] = useState<AdmissionCycleOut[]>([])
  const [rules, setRules] = useState<AdmissionRuleOut[]>([])
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    Promise.all([api.cycles(), api.rules()])
      .then(([c, r]) => {
        setCycles(c)
        setRules(r)
      })
      .catch((e: Error) => setError(e.message))
      .finally(() => setLoading(false))
  }, [])

  return (
    <div>
      <PageHeader
        title="Admissions"
        subtitle="Admission cycles and eligibility rules with source citations."
      />
      {error && <ErrorBox message={error} />}
      {loading && <Loading label="Loading admission data…" />}
      {!loading && (
        <div className="space-y-8">
          <Card>
            <h2 className="text-lg font-semibold text-slate-900">Admission Cycles</h2>
            <div className="mt-4 overflow-x-auto">
              <table className="min-w-full divide-y divide-slate-200">
                <thead>
                  <tr className="text-left text-xs font-medium uppercase tracking-wide text-slate-500">
                    <th className="px-3 py-2">Cycle</th>
                    <th className="px-3 py-2">Session</th>
                    <th className="px-3 py-2">Scope</th>
                    <th className="px-3 py-2">Status</th>
                    <th className="px-3 py-2">Deadline</th>
                    <th className="px-3 py-2">Source</th>
                    <th className="px-3 py-2">Verification</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100 bg-white text-sm text-slate-700">
                  {cycles.map((cycle) => (
                    <tr key={cycle.id}>
                      <td className="px-3 py-2 font-medium text-slate-900">{cycle.name}</td>
                      <td className="px-3 py-2">{cycle.session}</td>
                      <td className="px-3 py-2">{cycle.program_scope ?? '—'}</td>
                      <td className="px-3 py-2">
                        <Badge status={cycle.status} />
                      </td>
                      <td className="px-3 py-2">{cycle.application_deadline ?? '—'}</td>
                      <td className="px-3 py-2">
                        <SourceLink url={cycle.source_url} title={null} />
                      </td>
                      <td className="px-3 py-2">
                        <Badge status={cycle.verification_status} />
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </Card>

          <Card>
            <h2 className="text-lg font-semibold text-slate-900">Admission Rules</h2>
            <div className="mt-4 overflow-x-auto">
              <table className="min-w-full divide-y divide-slate-200">
                <thead>
                  <tr className="text-left text-xs font-medium uppercase tracking-wide text-slate-500">
                    <th className="px-3 py-2">Rule</th>
                    <th className="px-3 py-2">Program Scope</th>
                    <th className="px-3 py-2">Type</th>
                    <th className="px-3 py-2">Min Requirements</th>
                    <th className="px-3 py-2">Source</th>
                    <th className="px-3 py-2">Verification</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100 bg-white text-sm text-slate-700">
                  {rules.map((rule) => (
                    <tr key={rule.id}>
                      <td className="px-3 py-2">
                        <div className="font-medium text-slate-900">{rule.title}</div>
                        <p className="mt-1 text-xs text-slate-500">{rule.text}</p>
                      </td>
                      <td className="px-3 py-2">{rule.program_scope ?? '—'}</td>
                      <td className="px-3 py-2">{rule.rule_type}</td>
                      <td className="px-3 py-2 text-xs">
                        {rule.min_hssc_percent !== null && <div>HSSC: {rule.min_hssc_percent}%</div>}
                        {rule.min_mdcat_percent !== null && <div>MDCAT: {rule.min_mdcat_percent}%</div>}
                        {rule.min_entrance_percent !== null && <div>Entrance: {rule.min_entrance_percent}%</div>}
                        {rule.required_subjects?.length ? (
                          <div>Subjects: {rule.required_subjects.join(', ')}</div>
                        ) : null}
                      </td>
                      <td className="px-3 py-2">
                        <SourceLink url={rule.source_url} title={null} />
                      </td>
                      <td className="px-3 py-2">
                        <Badge status={rule.verification_status} />
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </Card>
        </div>
      )}
    </div>
  )
}