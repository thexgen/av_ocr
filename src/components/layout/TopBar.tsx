import { MobileMenuButton } from './Sidebar'

export function TopBar({ onMenuOpen }: { onMenuOpen: () => void }) {
  return (
    <header className="sticky top-0 z-30 border-b border-accent-400/10 bg-navy-950/65 backdrop-blur-xl">
      <div className="flex h-14 items-center justify-between gap-3 px-4 sm:px-6">
        <div className="flex items-center gap-3">
          <MobileMenuButton onClick={onMenuOpen} />
          <div className="hidden leading-tight sm:block lg:hidden">
            <div className="text-sm font-bold text-white">Asset Vantage</div>
            <div className="text-[11px] text-slate-500">Wealth OS</div>
          </div>
        </div>

        <div className="flex items-center gap-3">
          <div className="hidden sm:flex flex-col items-end leading-tight">
            <span className="text-xs font-semibold text-slate-200">Krishna Deval</span>
            <span className="text-[10px] text-slate-500">Family Office</span>
          </div>
          <div className="flex h-9 w-9 items-center justify-center rounded-full border border-accent-400/30 bg-gradient-to-br from-accent-400/30 to-accent-700/40 text-xs font-bold text-accent-400">
            KD
          </div>
        </div>
      </div>
    </header>
  )
}
