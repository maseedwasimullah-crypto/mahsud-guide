import { useState } from 'react'
import { NavLink, Outlet } from 'react-router-dom'
import Clock from './Clock'

const NAV = [
  { to: '/', label: 'Home', end: true },
  { to: '/assistant', label: 'AI Assistant' },
  { to: '/admissions', label: 'Admissions' },
  { to: '/calculator', label: 'Calculator' },
  { to: '/programs', label: 'Programs' },
  { to: '/institutions', label: 'Institutes' },
  { to: '/campuses', label: 'Campuses' },
  { to: '/policies', label: 'Policies' },
  { to: '/sources', label: 'Sources' },
  { to: '/about', label: 'About' },
  { to: '/admin', label: 'Admin' },
]

export default function Layout() {
  const [open, setOpen] = useState(false)
  return (
    <div className="min-h-screen">
      <header className="sticky top-0 z-40 border-b border-slate-200 bg-white/90 backdrop-blur">
        <div className="mx-auto flex max-w-6xl items-center justify-between gap-4 px-4 py-3">
          <NavLink to="/" className="flex items-center gap-2 font-bold text-slate-900">
            <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-emerald-600 text-sm font-black text-white">
              M
            </span>
            <span>
              MAHSUDo<span className="text-emerald-700">-guide</span>
            </span>
          </NavLink>
          <nav className="hidden items-center gap-1 lg:flex">
            {NAV.map((item) => (
              <NavLink
                key={item.to}
                to={item.to}
                end={item.end}
                className={({ isActive }) =>
                  `rounded-lg px-3 py-1.5 text-sm font-medium transition ${
                    isActive ? 'bg-emerald-50 text-emerald-800' : 'text-slate-600 hover:bg-slate-100 hover:text-slate-900'
                  }`
                }
              >
                {item.label}
              </NavLink>
            ))}
          </nav>
          <div className="flex items-center gap-3">
            <Clock />
            <button
              type="button"
              className="rounded-lg border border-slate-200 px-3 py-1.5 text-sm lg:hidden"
              onClick={() => setOpen((v) => !v)}
              aria-expanded={open}
              aria-label="Toggle navigation"
            >
              {open ? 'Close' : 'Menu'}
            </button>
          </div>
        </div>
        {open && (
          <nav className="grid grid-cols-2 gap-1 border-t border-slate-100 px-4 py-2 lg:hidden">
            {NAV.map((item) => (
              <NavLink
                key={item.to}
                to={item.to}
                end={item.end}
                onClick={() => setOpen(false)}
                className={({ isActive }) =>
                  `rounded-lg px-3 py-2 text-sm font-medium ${
                    isActive ? 'bg-emerald-50 text-emerald-800' : 'text-slate-600 hover:bg-slate-100'
                  }`
                }
              >
                {item.label}
              </NavLink>
            ))}
          </nav>
        )}
      </header>

      <main className="mx-auto max-w-6xl px-4 py-8">
        <Outlet />
      </main>

      <footer className="border-t border-slate-200 bg-white">
        <div className="mx-auto max-w-6xl px-4 py-6 text-sm text-slate-500">
          <p>
            <strong className="text-slate-700">MAHSUDo-guide</strong> is an independent research
            project built from official KMU, PNMC and HEC sources. It is not affiliated with,
            endorsed by, or operated by Khyber Medical University or any regulatory body.
          </p>
          <p className="mt-2">
            Every figure and rule shown here cites its official source. Always confirm the current
            requirement on the official page before applying.
          </p>
        </div>
      </footer>
    </div>
  )
}
