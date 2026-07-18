import { ChevronLeft, ChevronRight } from 'lucide-react'

export const DEFAULT_PAGE_SIZE = 10

type TablePaginationProps = {
  page: number
  pageSize?: number
  total: number
  onPageChange: (page: number) => void
}

export function TablePagination({
  page,
  pageSize = DEFAULT_PAGE_SIZE,
  total,
  onPageChange,
}: TablePaginationProps) {
  const totalPages = Math.max(1, Math.ceil(total / pageSize))
  const safePage = Math.min(Math.max(1, page), totalPages)
  const from = total === 0 ? 0 : (safePage - 1) * pageSize + 1
  const to = Math.min(safePage * pageSize, total)

  if (total === 0) return null

  return (
    <div className="flex flex-col gap-3 border-t border-white/5 px-4 py-3 sm:flex-row sm:items-center sm:justify-between">
      <p className="text-xs text-slate-500">
        Showing{' '}
        <span className="font-medium text-slate-300">
          {from}–{to}
        </span>{' '}
        of <span className="font-medium text-slate-300">{total}</span>
      </p>
      <div className="flex items-center gap-1.5">
        <button
          type="button"
          disabled={safePage <= 1}
          onClick={() => onPageChange(safePage - 1)}
          className="inline-flex h-8 items-center gap-1 rounded-lg border border-white/10 bg-white/[0.02] px-2.5 text-xs font-semibold text-slate-300 transition-colors hover:border-accent-400/30 hover:text-white disabled:cursor-not-allowed disabled:opacity-40"
        >
          <ChevronLeft className="h-3.5 w-3.5" />
          Prev
        </button>
        <span className="min-w-[4.5rem] text-center font-mono text-xs text-slate-400">
          {safePage} / {totalPages}
        </span>
        <button
          type="button"
          disabled={safePage >= totalPages}
          onClick={() => onPageChange(safePage + 1)}
          className="inline-flex h-8 items-center gap-1 rounded-lg border border-white/10 bg-white/[0.02] px-2.5 text-xs font-semibold text-slate-300 transition-colors hover:border-accent-400/30 hover:text-white disabled:cursor-not-allowed disabled:opacity-40"
        >
          Next
          <ChevronRight className="h-3.5 w-3.5" />
        </button>
      </div>
    </div>
  )
}

export function paginateSlice<T>(items: T[], page: number, pageSize = DEFAULT_PAGE_SIZE): T[] {
  const totalPages = Math.max(1, Math.ceil(items.length / pageSize))
  const safePage = Math.min(Math.max(1, page), totalPages)
  const start = (safePage - 1) * pageSize
  return items.slice(start, start + pageSize)
}
