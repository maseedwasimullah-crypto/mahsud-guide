import { useEffect, useState } from 'react'
import { api } from '../lib/api'
import { Card, ErrorBox, Loading, PageHeader } from '../components/ui'

export default function Admin() {
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [token, setToken] = useState(localStorage.getItem('mahsud_token') ?? '')
  const [role, setRole] = useState(localStorage.getItem('mahsud_role') ?? '')
  const [stats, setStats] = useState<Record<string, number> | null>(null)
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    if (token) {
      let active = true
      setLoading(true)
      api
        .adminStats()
        .then((s) => {
          if (active) setStats(s)
        })
        .catch((e: Error) => {
          if (active) setError(e.message)
        })
        .finally(() => {
          if (active) setLoading(false)
        })
      return () => {
        active = false
      }
    }
  }, [token])

  const login = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')
    setLoading(true)
    try {
      const res = await api.login(email, password)
      setToken(res.access_token)
      setRole(res.role)
    } catch (e) {
      if (e instanceof Error) setError(e.message)
    } finally {
      setLoading(false)
    }
  }

  const logout = () => {
    api.logout()
    setToken('')
    setRole('')
    setStats(null)
  }

  return (
    <div>
      <PageHeader title="Admin" subtitle="Admin area for verified staff (mock login in dev)." />
      {error && <ErrorBox message={error} />}
      {!token ? (
        <Card>
          <form onSubmit={login} className="grid gap-4 md:w-1/2">
            <div>
              <label className="mb-1 block text-sm font-medium text-slate-700">Email</label>
              <input
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="admin@example.com"
                className="w-full rounded-lg border border-slate-300 px-3 py-2 shadow-sm outline-none focus:border-emerald-500 focus:ring-2 focus:ring-emerald-200"
              />
            </div>
            <div>
              <label className="mb-1 block text-sm font-medium text-slate-700">Password</label>
              <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="w-full rounded-lg border border-slate-300 px-3 py-2 shadow-sm outline-none focus:border-emerald-500 focus:ring-2 focus:ring-emerald-200"
              />
            </div>
            <div>
              <button
                type="submit"
                disabled={loading}
                className="rounded-lg bg-emerald-700 px-4 py-2 font-semibold text-white shadow-sm hover:bg-emerald-800 disabled:cursor-not-allowed disabled:opacity-50"
              >
                {loading ? 'Logging in…' : 'Login'}
              </button>
            </div>
          </form>
        </Card>
      ) : (
        <div className="space-y-6">
          <Card>
            <div className="flex items-center justify-between">
              <div>
                <p className="font-medium text-slate-900">Logged in as {email || localStorage.getItem('mahsud_email')}</p>
                <p className="text-sm text-slate-500">Role: {role}</p>
              </div>
              <button
                onClick={logout}
                className="rounded-lg border border-slate-300 px-4 py-2 text-sm font-medium hover:bg-slate-50"
              >
                Logout
              </button>
            </div>
          </Card>
          <Card>
            <h2 className="text-lg font-semibold text-slate-900">Admin Stats</h2>
            {loading && <Loading label="Loading stats…" />}
            {stats && (
              <div className="mt-4 grid grid-cols-2 gap-3 md:grid-cols-4">
                {Object.entries(stats).map(([k, v]) => (
                  <div key={k} className="rounded-lg border border-slate-200 p-3 text-center">
                    <div className="text-2xl font-bold text-slate-900">{v}</div>
                    <div className="mt-1 text-xs uppercase tracking-wide text-slate-500">{k.replace(/_/g, ' ')}</div>
                  </div>
                ))}
              </div>
            )}
          </Card>
        </div>
      )}
    </div>
  )
}