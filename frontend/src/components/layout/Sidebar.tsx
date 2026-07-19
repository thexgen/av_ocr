import { useEffect, useLayoutEffect, useRef, useState } from 'react'
import { createPortal } from 'react-dom'
import { Link, useLocation } from 'react-router-dom'
import { AnimatePresence, motion } from 'framer-motion'
import {
  ChevronDown,
  Hexagon,
  Menu,
  PanelLeftClose,
  PanelLeftOpen,
  X,
} from 'lucide-react'
import {
  getVisibleNavigation,
  isNavGroup,
  type NavGroup,
  type NavLeaf,
} from '../../data/navigation'

export const SIDEBAR_EXPANDED = 260
export const SIDEBAR_COLLAPSED = 76
const STORAGE_KEY = 'av.sidebar.expanded'

function pathActive(pathname: string, path?: string) {
  if (!path) return false
  if (path === '/') return pathname === '/'
  return pathname === path || pathname.startsWith(`${path}/`)
}

function groupHasActive(pathname: string, group: NavGroup) {
  return group.children.some((c) => pathActive(pathname, c.path))
}

function readExpanded(): boolean {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    // Default collapsed — more canvas; expand when needed
    if (raw === null) return false
    return raw === '1'
  } catch {
    return false
  }
}

function LeafLink({
  item,
  nested,
  collapsed,
  onNavigate,
}: {
  item: NavLeaf
  nested?: boolean
  collapsed?: boolean
  onNavigate?: () => void
}) {
  const location = useLocation()
  const active = pathActive(location.pathname, item.path)
  const Icon = item.icon

  const className = `group relative flex w-full items-center gap-2.5 rounded-xl text-sm font-medium transition-colors ${
    collapsed ? 'justify-center px-0 py-2.5' : nested ? 'px-3 py-2 pl-3' : 'px-3 py-2'
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
          className={`absolute inset-0 border border-accent-400/25 bg-accent-500/15 ${
            collapsed ? 'rounded-xl' : 'rounded-xl'
          }`}
          transition={{ type: 'spring', stiffness: 380, damping: 32 }}
        />
      )}
      <Icon
        className={`relative z-10 h-4 w-4 shrink-0 ${
          active && !item.soon ? 'text-accent-400' : ''
        }`}
      />
      {!collapsed && (
        <>
          <span className="relative z-10 truncate">{item.label}</span>
          {item.soon && (
            <span className="relative z-10 ml-auto rounded-md border border-white/5 bg-white/[0.03] px-1.5 py-0.5 text-[10px] font-semibold uppercase tracking-wide text-slate-600">
              Soon
            </span>
          )}
        </>
      )}
    </>
  )

  if (item.soon || !item.path) {
    return (
      <div className={className} title={item.label}>
        {content}
      </div>
    )
  }

  return (
    <Link to={item.path} className={className} onClick={onNavigate} title={item.label}>
      {content}
    </Link>
  )
}

function FlyoutMenu({
  anchor,
  group,
  onClose,
  onNavigate,
}: {
  anchor: DOMRect
  group: NavGroup
  onClose: () => void
  onNavigate?: () => void
}) {
  const location = useLocation()
  const ref = useRef<HTMLDivElement>(null)

  useEffect(() => {
    const onDoc = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) onClose()
    }
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose()
    }
    document.addEventListener('mousedown', onDoc)
    document.addEventListener('keydown', onKey)
    return () => {
      document.removeEventListener('mousedown', onDoc)
      document.removeEventListener('keydown', onKey)
    }
  }, [onClose])

  const top = Math.min(anchor.top, window.innerHeight - 280)

  return createPortal(
    <motion.div
      ref={ref}
      initial={{ opacity: 0, x: -8, scale: 0.96 }}
      animate={{ opacity: 1, x: 0, scale: 1 }}
      exit={{ opacity: 0, x: -6, scale: 0.97 }}
      transition={{ duration: 0.2, ease: [0.22, 1, 0.36, 1] }}
      style={{ top, left: SIDEBAR_COLLAPSED + 8 }}
      className="fixed z-[60] w-56 overflow-hidden rounded-2xl border border-accent-400/20 bg-navy-900/95 p-2 shadow-[0_20px_50px_rgba(0,0,0,0.55)] backdrop-blur-2xl"
    >
      <div className="mb-1.5 px-2.5 py-1.5 text-[11px] font-semibold uppercase tracking-wider text-slate-500">
        {group.label}
      </div>
      <ul className="space-y-0.5">
        {group.children.map((child) => {
          const active = pathActive(location.pathname, child.path)
          const Icon = child.icon
          const base =
            'flex w-full items-center gap-2.5 rounded-xl px-2.5 py-2 text-sm font-medium transition-colors'
          if (child.soon || !child.path) {
            return (
              <li key={child.id}>
                <div className={`${base} cursor-not-allowed text-slate-600`}>
                  <Icon className="h-3.5 w-3.5" />
                  <span className="truncate">{child.label}</span>
                  <span className="ml-auto text-[10px] uppercase text-slate-600">Soon</span>
                </div>
              </li>
            )
          }
          return (
            <li key={child.id}>
              <Link
                to={child.path}
                onClick={() => {
                  onNavigate?.()
                  onClose()
                }}
                className={`${base} ${
                  active
                    ? 'border border-accent-400/25 bg-accent-500/15 text-white'
                    : 'text-slate-300 hover:bg-white/[0.04] hover:text-white'
                }`}
              >
                <Icon
                  className={`h-3.5 w-3.5 ${active ? 'text-accent-400' : ''}`}
                />
                <span className="truncate">{child.label}</span>
              </Link>
            </li>
          )
        })}
      </ul>
    </motion.div>,
    document.body,
  )
}

function NavGroupItem({
  group,
  collapsed,
  onNavigate,
}: {
  group: NavGroup
  collapsed?: boolean
  onNavigate?: () => void
}) {
  const location = useLocation()
  const hasActive = groupHasActive(location.pathname, group)
  const [open, setOpen] = useState(hasActive)
  const [flyout, setFlyout] = useState(false)
  const btnRef = useRef<HTMLButtonElement>(null)
  const Icon = group.icon

  useEffect(() => {
    if (hasActive && !collapsed) setOpen(true)
  }, [hasActive, collapsed])

  if (collapsed) {
    return (
      <div className="relative">
        <button
          ref={btnRef}
          type="button"
          title={group.label}
          onClick={() => setFlyout((v) => !v)}
          className={`flex w-full items-center justify-center rounded-xl py-2.5 transition-colors ${
            hasActive || flyout
              ? 'text-white'
              : 'text-slate-400 hover:text-slate-100'
          }`}
        >
          {(hasActive || flyout) && (
            <span className="absolute inset-0 rounded-xl border border-accent-400/25 bg-accent-500/15" />
          )}
          <Icon
            className={`relative z-10 h-4 w-4 ${hasActive ? 'text-accent-400' : ''}`}
          />
        </button>
        <AnimatePresence>
          {flyout && btnRef.current && (
            <FlyoutMenu
              anchor={btnRef.current.getBoundingClientRect()}
              group={group}
              onClose={() => setFlyout(false)}
              onNavigate={onNavigate}
            />
          )}
        </AnimatePresence>
      </div>
    )
  }

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
            <ul className="relative mt-1 ml-5 space-y-0.5 border-l border-accent-400/15 py-1 pl-3">
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
  expanded,
  onExpandedChange,
}: {
  mobileOpen: boolean
  onClose: () => void
  expanded: boolean
  onExpandedChange: (next: boolean) => void
}) {
  const location = useLocation()

  useEffect(() => {
    onClose()
  }, [location.pathname]) // eslint-disable-line react-hooks/exhaustive-deps

  const toggleExpanded = () => {
    onExpandedChange(!expanded)
  }

  const visibleNav = getVisibleNavigation()

  const navItems = (
    <nav className={`flex flex-1 flex-col gap-1 py-4 ${expanded ? 'px-3' : 'px-2.5'}`}>
      {visibleNav.map((item) =>
        isNavGroup(item) ? (
          <NavGroupItem
            key={item.id}
            group={item}
            collapsed={!expanded}
            onNavigate={onClose}
          />
        ) : (
          <LeafLink
            key={item.id}
            item={item}
            collapsed={!expanded}
            onNavigate={onClose}
          />
        ),
      )}
    </nav>
  )

  return (
    <>
      {/* Desktop — collapsible rail */}
      <motion.aside
        initial={false}
        animate={{ width: expanded ? SIDEBAR_EXPANDED : SIDEBAR_COLLAPSED }}
        transition={{ type: 'spring', stiffness: 320, damping: 34 }}
        className="fixed inset-y-0 left-0 z-40 hidden flex-col border-r border-accent-400/10 bg-navy-950/80 backdrop-blur-2xl lg:flex"
      >
        <div
          className={`flex items-center border-b border-white/5 ${
            expanded ? 'gap-2 px-3 py-4' : 'flex-col gap-3 px-2 py-4'
          }`}
        >
          <Link
            to="/"
            className={`group flex min-w-0 items-center ${
              expanded ? 'flex-1 gap-3 px-1' : 'justify-center'
            }`}
            title="Asset Vantage"
          >
            <div className="relative flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-gradient-to-br from-accent-500 to-accent-700 glow-blue">
              <Hexagon className="h-5 w-5 text-white" strokeWidth={2.2} />
            </div>
            <AnimatePresence initial={false}>
              {expanded && (
                <motion.div
                  initial={{ opacity: 0, x: -6 }}
                  animate={{ opacity: 1, x: 0 }}
                  exit={{ opacity: 0, x: -4 }}
                  transition={{ duration: 0.18 }}
                  className="min-w-0 leading-tight"
                >
                  <div className="truncate text-sm font-bold tracking-tight text-white transition-colors group-hover:text-accent-400">
                    Asset Vantage
                  </div>
                  <div className="text-[11px] font-medium text-slate-500">Wealth OS</div>
                </motion.div>
              )}
            </AnimatePresence>
          </Link>

          <button
            type="button"
            onClick={toggleExpanded}
            title={expanded ? 'Collapse sidebar' : 'Expand sidebar'}
            className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg border border-white/10 bg-white/[0.03] text-slate-400 transition-colors hover:border-accent-400/30 hover:bg-accent-500/10 hover:text-accent-400"
          >
            {expanded ? (
              <PanelLeftClose className="h-3.5 w-3.5" />
            ) : (
              <PanelLeftOpen className="h-3.5 w-3.5" />
            )}
          </button>
        </div>

        {navItems}

        <div className={`border-t border-white/5 ${expanded ? 'px-4 py-4' : 'px-2 py-3'}`}>
          {expanded ? (
            <p className="text-[10px] uppercase tracking-wider text-slate-600">
              Bank Cash live · more modules soon
            </p>
          ) : (
            <div
              className="mx-auto h-1.5 w-1.5 rounded-full bg-accent-400/50"
              title="Bank Cash live"
            />
          )}
        </div>
      </motion.aside>

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
                    <div className="truncate text-sm font-bold tracking-tight text-white transition-colors group-hover:text-accent-400">
                      Asset Vantage
                    </div>
                    <div className="text-[11px] font-medium text-slate-500">Wealth OS</div>
                  </div>
                </Link>
                <button
                  type="button"
                  onClick={onClose}
                  className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg text-slate-400 hover:bg-white/5 hover:text-white"
                >
                  <X className="h-4 w-4" />
                </button>
              </div>
              <nav className="flex flex-1 flex-col gap-1 px-3 py-4">
                {visibleNav.map((item) =>
                  isNavGroup(item) ? (
                    <NavGroupItem
                      key={item.id}
                      group={item}
                      onNavigate={onClose}
                    />
                  ) : (
                    <LeafLink key={item.id} item={item} onNavigate={onClose} />
                  ),
                )}
              </nav>
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

export function useSidebarExpanded() {
  const [expanded, setExpanded] = useState(readExpanded)

  useLayoutEffect(() => {
    try {
      localStorage.setItem(STORAGE_KEY, expanded ? '1' : '0')
    } catch {
      /* ignore */
    }
  }, [expanded])

  return [expanded, setExpanded] as const
}
