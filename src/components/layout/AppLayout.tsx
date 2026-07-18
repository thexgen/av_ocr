import { useState, type CSSProperties } from 'react'
import { Outlet, useLocation } from 'react-router-dom'
import { AnimatePresence, motion } from 'framer-motion'
import {
  Sidebar,
  SIDEBAR_COLLAPSED,
  SIDEBAR_EXPANDED,
  useSidebarExpanded,
} from './Sidebar'
import { TopBar } from './TopBar'

export function AppLayout() {
  const location = useLocation()
  const [mobileOpen, setMobileOpen] = useState(false)
  const [expanded, setExpanded] = useSidebarExpanded()

  return (
    <div className="relative min-h-screen">
      <div className="app-bg" aria-hidden />
      <Sidebar
        mobileOpen={mobileOpen}
        onClose={() => setMobileOpen(false)}
        expanded={expanded}
        onExpandedChange={setExpanded}
      />
      <div
        className="min-h-screen transition-[padding] duration-300 ease-[cubic-bezier(0.22,1,0.36,1)] lg:pl-[var(--sidebar-w)]"
        style={
          {
            ['--sidebar-w']: `${expanded ? SIDEBAR_EXPANDED : SIDEBAR_COLLAPSED}px`,
          } as CSSProperties
        }
      >
        <TopBar onMenuOpen={() => setMobileOpen(true)} />
        <main className="mx-auto max-w-7xl px-4 py-6 sm:px-6 lg:px-8 lg:py-8">
          <AnimatePresence mode="wait">
            <motion.div
              key={location.pathname}
              initial={{ opacity: 0, y: 12 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -8 }}
              transition={{ duration: 0.35, ease: [0.22, 1, 0.36, 1] }}
            >
              <Outlet />
            </motion.div>
          </AnimatePresence>
        </main>
      </div>
    </div>
  )
}
