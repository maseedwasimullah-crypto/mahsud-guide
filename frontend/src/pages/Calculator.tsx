import { useEffect, useState } from 'react'
import { api } from '../lib/api'
import { Badge, Card, ErrorBox, Loading, PageHeader, SourceLink } from '../components/ui'
import type { AggregateResponse, EligibilityResponse, FormulaOut } from '../lib/types'

export default function Calculator() {
  const [formulas, setFormulas] = useState<FormulaOut[]>([])
  const [selected, setSelected] = useState<number | null>(null)
  const [inputs, setInputs] = useState<Record<string, any>>({})
  const [aggregate, setAggregate] = useState<AggregateResponse | null>(null)
  const [eligibility, setEligibility] = useState<EligibilityResponse | null>(null)
  const [eligLoading, setEligLoading] = useState(false)
  const [loading, setLoading] = useState(true)
  const [calcLoading, setCalcLoading] = useState(false)
  const [error, setError] = useState('')
  const [eligError, setEligError] = useState('')

  useEffect(() => {
    api
      .formulas()
      .then((f) => {
        setFormulas(f.filter((x) => x.usable))
        if (f.length > 0) {
          const first = f.find((x) => x.usable) ?? f[0]
          setSelected(first.id)
          // initialize inputs
          const initial: Record<string, any> = {}
          for (const c of first.components) {
            initial[c.key] = ''
          }
          setInputs(initial)
        }
      })
      .catch((e: Error) => setError(e.message))
      .finally(() => setLoading(false))
  }, [])

  const changeFormula = (id: number) => {
    setSelected(id)
    const f = formulas.find((x) => x.id === id)
    const initial: Record<string, any> = {}
    if (f) {
      for (const c of f.components) {
        initial[c.key] = ''
      }
    }
    setInputs(initial)
    setAggregate(null)
    setEligibility(null)
  }

  const handleInput = (key: string, value: string) => {
    setInputs((prev) => ({ ...prev, [key]: value }))
  }

  const calculate = async (e: React.FormEvent) => {
    e.preventDefault()
    if (selected === null) return
    setError('')
    setCalcLoading(true)
    setAggregate(null)
    try {
      const payload: Record<string, any> = {}
      const f = formulas.find((x) => x.id === selected)!
      for (const c of f.components) {
        const v = inputs[c.key]
        if (v === '' || v === undefined) {
          // let API validate; but try to pass numbers
          continue
        }
        payload[c.key] = Number(v)
      }
      const res = await api.calculate(selected, payload)
      setAggregate(res)
      // also run eligibility if we have basic inputs
      await runEligibility(f, payload)
    } catch (err) {
      if (err instanceof Error) setError(err.message)
      else setError('Calculation failed')
    } finally {
      setCalcLoading(false)
    }
  }

  const runEligibility = async (f: FormulaOut, vals: Record<string, any>) => {
    setEligError('')
    setEligLoading(true)
    try {
      const body: Record<string, any> = {}
      if (vals.hssc_percent !== undefined && !isNaN(vals.hssc_percent)) body.hssc_percent = vals.hssc_percent
      if (vals.mdcat_percent !== undefined && !isNaN(vals.mdcat_percent)) body.mdcat_percent = vals.mdcat_percent
      if (vals.entrance_test_percent !== undefined && !isNaN(vals.entrance_test_percent)) body.entrance_test_percent = vals.entrance_test_percent
      if (vals.entrance !== undefined && !isNaN(vals.entrance)) body.entrance_test_percent = Number(vals.entrance)
      const res = await api.checkEligibility(body)
      setEligibility(res)
    } catch (err) {
      if (err instanceof Error) setEligError(err.message)
      else setEligError('Eligibility check failed')
    } finally {
      setEligLoading(false)
    }
  }

  const f = selected ? formulas.find((x) => x.id === selected) : null

  return (
    <div>
      <PageHeader
        title="Merit Calculator"
        subtitle="Deterministic aggregate calculation using verified formulas. All results cite official sources."
      />
      {error && <ErrorBox message={error} />}
      {loading && <Loading label="Loading verified formulas…" />}
      {!loading && (
        <div className="space-y-6">
          <Card>
            <h2 className="text-lg font-semibold text-slate-900">Select Formula</h2>
            <select
              value={selected ?? ''}
              onChange={(e) => changeFormula(Number(e.target.value))}
              className="mt-2 w-full rounded-lg border border-slate-300 px-3 py-2 shadow-sm outline-none focus:border-emerald-500 focus:ring-2 focus:ring-emerald-200 md:w-2/3"
            >
              {formulas.map((x) => (
                <option key={x.id} value={x.id}>
                  {x.name} ({x.admission_session}, {x.program_scope})
                </option>
              ))}
            </select>
            {f && (
              <div className="mt-3 text-sm text-slate-600">
                <div>Rounding: {f.rounding} decimals</div>
                <div>
                  Source: <SourceLink url={f.source_url} title={f.source_title} />
                </div>
                {f.explanation && <p className="mt-2">{f.explanation}</p>}
              </div>
            )}
          </Card>

          {f && (
            <Card>
              <h2 className="text-lg font-semibold text-slate-900">Enter Components</h2>
              <form onSubmit={calculate} className="mt-4 grid gap-4 md:grid-cols-2">
                {f.components.map((c) => (
                  <div key={c.key}>
                    <label className="mb-1 block text-sm font-medium text-slate-700">
                      {c.label} ({Math.round(c.weight * 100)}%)
                    </label>
                    <input
                      type="number"
                      step="0.01"
                      min="0"
                      max="100"
                      value={inputs[c.key] ?? ''}
                      onChange={(e) => handleInput(c.key, e.target.value)}
                      placeholder="85.00"
                      className="w-full rounded-lg border border-slate-300 px-3 py-2 shadow-sm outline-none focus:border-emerald-500 focus:ring-2 focus:ring-emerald-200"
                    />
                  </div>
                ))}
                <div className="md:col-span-2 flex justify-end">
                  <button
                    type="submit"
                    disabled={calcLoading}
                    className="rounded-lg bg-emerald-700 px-5 py-2.5 font-semibold text-white shadow-sm hover:bg-emerald-800 disabled:cursor-not-allowed disabled:opacity-50"
                  >
                    {calcLoading ? 'Calculating…' : 'Calculate'}
                  </button>
                </div>
              </form>
            </Card>
          )}

          {aggregate && (
            <Card>
              <div className="flex items-center justify-between">
                <h2 className="text-lg font-semibold text-slate-900">Result</h2>
                <Badge status="verified" />
              </div>
              <div className="mt-4 grid gap-4 md:grid-cols-2">
                <div>
                  <div className="text-3xl font-bold text-emerald-800">{aggregate.aggregate.toFixed(aggregate.rounding)}%</div>
                  <p className="mt-1 text-sm text-slate-500">{aggregate.formula_name}</p>
                  <p className="mt-1 text-sm text-slate-500">
                    Session: {aggregate.admission_session} • Program scope: {aggregate.program_scope}
                  </p>
                </div>
                <div>
                  <h3 className="font-medium text-slate-800">Components</h3>
                  <ul className="mt-2 space-y-2 text-sm text-slate-600">
                    {aggregate.components.map((c) => (
                      <li key={c.key} className="flex items-center justify-between rounded bg-slate-50 px-2 py-1">
                        <span>{c.label}</span>
                        <span>
                          {c.percent.toFixed(2)}% × {Math.round(c.weight * 100)}% = {c.contribution.toFixed(aggregate.rounding)}%
                        </span>
                      </li>
                    ))}
                  </ul>
                </div>
              </div>
              <div className="mt-4 text-sm text-slate-600">
                <SourceLink url={aggregate.source.url} title={aggregate.source.title} />
              </div>
              {aggregate.explanation && <p className="mt-2 text-sm text-slate-500">{aggregate.explanation}</p>}
              <ul className="mt-3 list-disc space-y-1 pl-5 text-xs text-slate-500">
                {aggregate.limitations.map((l, i) => (
                  <li key={i}>{l}</li>
                ))}
              </ul>
            </Card>
          )}

          {(eligLoading || eligibility || eligError) && (
            <Card>
              <h2 className="text-lg font-semibold text-slate-900">Eligibility (rule-based)</h2>
              {eligLoading && <Loading label="Checking eligibility…" />}
              {eligError && <ErrorBox message={eligError} />}
              {eligibility && (
                <div className="mt-4 space-y-4">
                  <div className="flex items-center justify-between">
                    <div>
                      <div className="text-lg font-semibold text-slate-800">
                        Status: <span className="capitalize">{eligibility.status.replace(/_/g, ' ')}</span>
                      </div>
                      {eligibility.program && <p className="text-sm text-slate-500">Program context: {eligibility.program}</p>}
                    </div>
                    <Badge status={eligibility.status} />
                  </div>
                  {eligibility.evaluations.length > 0 && (
                    <div className="overflow-x-auto">
                      <table className="min-w-full divide-y divide-slate-200 text-sm">
                        <thead>
                          <tr className="text-left text-xs font-medium uppercase tracking-wide text-slate-500">
                            <th className="px-3 py-2">Rule</th>
                            <th className="px-3 py-2">Requirement</th>
                            <th className="px-3 py-2">Satisfied</th>
                            <th className="px-3 py-2">Source</th>
                          </tr>
                        </thead>
                        <tbody className="divide-y divide-slate-100">
                          {eligibility.evaluations.map((ev) => (
                            <tr key={ev.rule_id}>
                              <td className="px-3 py-2 font-medium text-slate-800">{ev.title}</td>
                              <td className="px-3 py-2 text-slate-600">{ev.requirement}</td>
                              <td className="px-3 py-2">
                                {ev.satisfied === null ? '—' : ev.satisfied ? 'Yes' : 'No'}
                              </td>
                              <td className="px-3 py-2">
                                <SourceLink url={ev.source_url} title={null} />
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  )}
                  {eligibility.missing_information.length > 0 && (
                    <div className="rounded bg-amber-50 p-3 text-sm text-amber-900">
                      Missing: {eligibility.missing_information.join('; ')}
                    </div>
                  )}
                  {eligibility.notes.length > 0 && (
                    <ul className="list-disc space-y-1 pl-5 text-xs text-slate-500">
                      {eligibility.notes.map((n, i) => (
                        <li key={i}>{n}</li>
                      ))}
                    </ul>
                  )}
                </div>
              )}
            </Card>
          )}
        </div>
      )}
    </div>
  )
}