import { useEffect, useMemo, useState } from 'react'
import { Link, useLocation } from 'react-router-dom'
import { AnimatePresence, motion } from 'framer-motion'
import { ChevronDown, Hexagon, Menu, X } from 'lucide-react'
import { isNavGroup, navigation, type NavGroup, type NavLeaf } from '../../data/navigation'

function pathActive(pathname: string, path?: string) {
  if (!path) return false
  if (path === '/') return pathname === '/'
  return pathname === path || pathname.startsWith(`${path}/`)
}

function groupHasActive(pathname: string, group: NavGroup) {
  return group.children.some((c) => pathActive(pathname, c.path))
}

function LeafLink({
  item,
  nested,
  onNavigate,
}: {
  item: NavLeaf
  nested?: boolean
  onNavigate?: () => void
}) {
  const location = useLocation()
  const active = pathActive(location.pathname, item.path)
  const Icon = item.icon

  const className = `group relative flex w-full items-center gap-2.5 rounded-xl px-3 py-2 text-sm font-medium transition-colors ${
    nested ? 'pl-3' : ''
  } ${
    item.soon
      ? 'cursor-not-allowed text-slate-600'
      : active
        ? 'text-white'
        : 'text-slate-400 hover:text-slate-100'
  }`

  const content = (
    <>
      {active && !item.soon && (
        <motion.span
          layoutId="sidebar-active"
          className="absolute inset-0 rounded-xl border border-accent-400/25 bg-accent-500/15"
          transition={{ type: 'spring', stiffness: 380, damping: 32 }}
        />
      )}
      <Icon
        className={`relative z-10 h-4 w-4 shrink-0 ${
          active && !item.soon ? 'text-accent-400' : ''
        }`}
      />
      <span className="relative z-10 truncate">{item.label}</span>
      {item.soon && (
        <span className="relative z-10 ml-auto rounded-md border border-white/5 bg-white/[0.03] px-1.5 py-0.5 text-[10px] font-semibold uppercase tracking-wide text-slate-600">
          Soon
        </span>
      )}
    </>
  )

  if (item.soon || !item.path) {
    return (
      <div className={className} title="Coming soon">
        {content}
      </div>
    )
  }

  return (
    <Link to={item.path} className={className} onClick={onNavigate}>
      {content}
    </Link>
  )
}

function NavGroupItem({
  group,
  onNavigate,
}: {
  group: NavGroup
  onNavigate?: () => void
}) {
  const location = useLocation()
  const hasActive = groupHasActive(location.pathname, group)
  const [open, setOpen] = useState(hasActive)
  const Icon = group.icon

  useEffect(() => {
    if (hasActive) setOpen(true)
  }, [hasActive])

  return (
    <div>
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        className={`flex w-full items-center gap-2.5 rounded-xl px-3 py-2 text-sm font-medium transition-colors ${
          hasActive ? 'text-white' : 'text-slate-400 hover:text-slate-100'
        }`}
      >
        <Icon className={`h-4 w-4 shrink-0 ${hasActive ? 'text-accent-400' : ''}`} />
        <span className="truncate">{group.label}</span>
        <motion.span
          animate={{ rotate: open ? 180 : 0 }}
          transition={{ duration: 0.22, ease: [0.22, 1, 0.36, 1] }}
          className="ml-auto"
        >
          <ChevronDown className="h-3.5 w-3.5 text-slate-500" />
        </motion.span>
      </button>

      <AnimatePresence initial={false}>
        {open && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.28, ease: [0.22, 1, 0.36, 1] }}
            className="overflow-hidden"
          >
            <ul className="relative mt-1 space-y-0.5 border-l border-accent-400/15 py-1 pl-3 ml-5">
              {group.children.map((child, i) => (
                <motion.li
                  key={child.id}
                  initial={{ opacity: 0, x: -8 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{
                    delay: i * 0.035,
                    duration: 0.25,
                    ease: [0.22, 1, 0.36, 1],
                  }}
                >
                  <LeafLink item={child} nested onNavigate={onNavigate} />
                </motion.li>
              ))}
            </ul>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}

export function Sidebar({
  mobileOpen,
  onClose,
}: {
  mobileOpen: boolean
  onClose: () => void
}) {
  const location = useLocation()

  useEffect(() => {
    onClose()
  }, [location.pathname]) // eslint-disable-line react-hooks/exhaustive-deps

  const navBody = useMemo(
    () => (
      <nav className="flex flex-1 flex-col gap-1 px-3 py-4">
        {navigation.map((item) =>
          isNavGroup(item) ? (
            <NavGroupItem key={item.id} group={item} onNavigate={onClose} />
          ) : (
            <LeafLink key={item.id} item={item} onNavigate={onClose} />
          ),
        )}
      </nav>
    ),
    [onClose],
  )

  const brand = (compactClose?: boolean) => (
    <div className="flex items-center gap-2 border-b border-white/5 px-3 py-4">
      <Link
        to="/"
        onClick={onClose}
        className="group flex min-w-0 flex-1 items-center gap-3 px-1"
      >
        <div className="relative flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-gradient-to-br from-accent-500 to-accent-700 glow-blue">
          <Hexagon className="h-5 w-5 text-white" strokeWidth={2.2} />
        </div>
        <div className="min-w-0 leading-tight">
          <div className="truncate text-sm font-bold tracking-tight text-white group-hover:text-accent-400 transition-colors">
            Asset Vantage
          </div>
          <div className="text-[11px] font-medium text-slate-500">Wealth OS</div>
        </div>
      </Link>
      {compactClose && (
        <button
          type="button"
          onClick={onClose}
          className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg text-slate-400 hover:bg-white/5 hover:text-white"
        >
          <X className="h-4 w-4" />
        </button>
      )}
    </div>
  )

  return (
    <>
      {/* Desktop */}
      <aside className="fixed inset-y-0 left-0 z-40 hidden w-[260px] flex-col border-r border-accent-400/10 bg-navy-950/80 backdrop-blur-2xl lg:flex">
        {brand()}
        {navBody}
        <div className="border-t border-white/5 px-4 py-4">
          <p className="text-[10px] uppercase tracking-wider text-slate-600">
            Bank Cash live · more modules soon
          </p>
        </div>
      </aside>

      {/* Mobile drawer */}
      <AnimatePresence>
        {mobileOpen && (
          <>
            <motion.button
              type="button"
              aria-label="Close menu"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="fixed inset-0 z-50 bg-navy-950/70 backdrop-blur-sm lg:hidden"
              onClick={onClose}
            />
            <motion.aside
              initial={{ x: -280 }}
              animate={{ x: 0 }}
              exit={{ x: -280 }}
              transition={{ type: 'spring', stiffness: 360, damping: 34 }}
              className="fixed inset-y-0 left-0 z-50 flex w-[280px] flex-col border-r border-accent-400/15 bg-navy-950/95 backdrop-blur-2xl lg:hidden"
            >
              {brand(true)}
              {navBody}
            </motion.aside>
          </>
        )}
      </AnimatePresence>
    </>
  )
}

export function MobileMenuButton({ onClick }: { onClick: () => void }) {
  return (
    <button
      type="button"
      onClick={onClick}
      className="flex h-9 w-9 items-center justify-center rounded-xl border border-white/10 bg-white/[0.03] text-slate-300 hover:text-white lg:hidden"
      aria-label="Open menu"
    >
      <Menu className="h-4 w-4" />
    </button>
  )
}
