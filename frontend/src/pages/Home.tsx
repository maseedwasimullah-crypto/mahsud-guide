import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../lib/api'
import { Card, Disclaimer, ErrorBox, Loading, Stat } from '../components/ui'
import type { AdmissionCycleOut, FormulaOut } from '../lib/types'

export default function Home() {
  const [quality, setQuality] = useState<{ counts: Record<string, number>; known_gaps: string[] } | null>(null)
  const [formulas, setFormulas] = useState<FormulaOut[]>([])
  const [cycles, setCycles] = useState<AdmissionCycleOut[]>([])
  const [error, setError] = useState('')

  useEffect(() => {
    Promise.all([api.dataQuality(), api.formulas(), api.cycles()])
      .then(([q, f, c]) => {
        setQuality(q)
        setFormulas(f.filter((formula) => formula.usable))
        setCycles(c.slice(0, 4))
      })
      .catch((e: Error) => setError(e.message))
  }, [])

  return (
    <div>
      <section className="rounded-2xl bg-gradient-to-br from-emerald-700 to-teal-800 p-8 text-white shadow-lg md:p-12">
        <h1 className="max-w-3xl text-4xl font-bold tracking-tight md:text-5xl">
          University guidance for KMU — with every answer traced to an official source.
        </h1>
        <p className="mt-4 max-w-2xl text-emerald-50">
          MAHSUDo-guide combines a retrieval-grounded AI assistant, a deterministic merit
          aggregate calculator and rule-based eligibility checks, all built from published KMU,
          PNMC and HEC documents.
        </p>
        <div className="mt-6 flex flex-wrap gap-3">
          <Link to="/assistant" className="rounded-lg bg-white px-5 py-2.5 font-semibold text-emerald-800 hover:bg-emerald-50">
            Ask the assistant
          </Link>
          <Link to="/calculator" className="rounded-lg border border-emerald-300 px-5 py-2.5 font-semibold text-white hover:bg-emerald-600">
            Calculate merit aggregate
          </Link>
        </div>
      </section>

      {error && (
        <div className="mt-6">
          <ErrorBox message={error} />
        </div>
      )}

      {quality && (
        <div className="mt-8 grid grid-cols-2 gap-3 md:grid-cols-5">
          <Stat label="Official sources" value={quality.counts.sources ?? 0} />
          <Stat label="Documents" value={quality.counts.documents ?? 0} />
          <Stat label="Programs" value={quality.counts.programs ?? 0} />
          <Stat label="Institutes" value={quality.counts.institutions ?? 0} />
          <Stat label="Verified docs" value={quality.counts.verified_documents ?? 0} />
        </div>
      )}

      <div className="mt-10 grid gap-6 lg:grid-cols-2">
        <Card>
          <h2 className="text-lg font-semibold text-slate-900">Merit formulas in the knowledge base</h2>
          {!formulas.length && !error && <Loading label="Loading formulas…" />}
          <ul className="mt-4 space-y-3">
            {formulas.map((formula) => (
              <li key={formula.id} className="rounded-lg border border-slate-100 bg-slate-50 p-3">
                <Link to="/calculator" className="font-medium text-emerald-800 hover:underline">
                  {formula.name}
                </Link>
                <p className="mt-1 text-sm text-slate-600">
                  Session {formula.admission_session} · {formula.program_scope}
                </p>
              </li>
            ))}
          </ul>
        </Card>

        <Card>
          <h2 className="text-lg font-semibold text-slate-900">Admission cycles</h2>
          <ul className="mt-4 space-y-3">
            {cycles.map((cycle) => (
              <li key={cycle.id} className="rounded-lg border border-slate-100 bg-slate-50 p-3">
                <div className="flex items-center justify-between gap-2">
                  <span className="font-medium text-slate-800">{cycle.name}</span>
                  <span
                    className={`rounded-full px-2 py-0.5 text-xs font-medium ${
                      cycle.status === 'open' ? 'bg-emerald-100 text-emerald-800' : 'bg-slate-200 text-slate-600'
                    }`}
                  >
                    {cycle.status}
                  </span>
                </div>
                <p className="mt-1 text-sm text-slate-600">
                  {cycle.program_scope ?? 'All programs'} · deadline{' '}
                  {cycle.application_deadline ?? 'not recorded'}
                </p>
              </li>
            ))}
          </ul>
          <Link to="/admissions" className="mt-4 inline-block text-sm font-medium text-emerald-700 hover:underline">
            All admission details →
          </Link>
        </Card>
      </div>

      {quality && quality.known_gaps.length > 0 && (
        <div className="mt-8">
          <Disclaimer>
            <strong>What this knowledge base does not know yet:</strong>
            <ul className="mt-2 list-disc space-y-1 pl-5">
              {quality.known_gaps.map((gap) => (
                <li key={gap}>{gap}</li>
              ))}
            </ul>
          </Disclaimer>
        </div>
      )}
    </div>
  )
}
