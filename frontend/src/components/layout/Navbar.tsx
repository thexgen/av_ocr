import { Link, useLocation } from 'react-router-dom'
import { motion } from 'framer-motion'
import {
  LayoutDashboard,
  Upload,
  Sparkles,
  Table2,
  CheckCircle2,
  Hexagon,
} from 'lucide-react'

const navItems = [
  { path: '/', label: 'Dashboard', icon: LayoutDashboard },
  { path: '/upload', label: 'Upload', icon: Upload },
  { path: '/processing', label: 'Processing', icon: Sparkles },
  { path: '/review', label: 'Review', icon: Table2 },
  { path: '/success', label: 'Success', icon: CheckCircle2 },
]

export function Navbar() {
  const location = useLocation()

  return (
    <header className="sticky top-0 z-40 border-b border-accent-400/10 bg-navy-950/70 backdrop-blur-xl">
      <div className="mx-auto flex h-16 max-w-7xl items-center justify-between px-4 sm:px-6 lg:px-8">
        <Link to="/" className="group flex items-center gap-3">
          <div className="relative flex h-9 w-9 items-center justify-center rounded-xl bg-gradient-to-br from-accent-500 to-accent-700 glow-blue">
            <Hexagon className="h-5 w-5 text-white" strokeWidth={2.2} />
          </div>
          <div className="leading-tight">
            <div className="text-sm font-bold tracking-tight text-white group-hover:text-accent-400 transition-colors">
              Aether Wealth
            </div>
            <div className="text-[11px] font-medium text-slate-400">
              AI Statement Import
            </div>
          </div>
        </Link>

        <nav className="hidden items-center gap-1 md:flex">
          {navItems.map(({ path, label, icon: Icon }) => {
            const active =
              path === '/'
                ? location.pathname === '/'
                : location.pathname.startsWith(path)

            return (
              <Link
                key={path}
                to={path}
                className="relative rounded-lg px-3 py-2 text-sm font-medium transition-colors"
              >
                <span
                  className={`relative z-10 flex items-center gap-1.5 ${
                    active ? 'text-white' : 'text-slate-400 hover:text-slate-200'
                  }`}
                >
                  <Icon className="h-3.5 w-3.5" />
                  {label}
                </span>
                {active && (
                  <motion.span
                    layoutId="nav-pill"
                    className="absolute inset-0 rounded-lg bg-accent-500/15 border border-accent-400/20"
                    transition={{ type: 'spring', stiffness: 380, damping: 30 }}
                  />
                )}
              </Link>
            )
          })}
        </nav>

        <div className="flex items-center gap-3">
          <div className="hidden sm:flex flex-col items-end leading-tight">
            <span className="text-xs font-semibold text-slate-200">Alex Morgan</span>
            <span className="text-[10px] text-slate-500">Senior Analyst</span>
          </div>
          <div className="flex h-9 w-9 items-center justify-center rounded-full bg-gradient-to-br from-accent-400/30 to-accent-700/40 border border-accent-400/30 text-xs font-bold text-accent-400">
            AM
          </div>
        </div>
      </div>
    </header>
  )
}
