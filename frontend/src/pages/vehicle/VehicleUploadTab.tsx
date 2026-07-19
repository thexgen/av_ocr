import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { AnimatePresence, motion } from 'framer-motion'
import {
  AlertCircle,
  CheckCircle2,
  FileUp,
  Loader2,
  Upload,
} from 'lucide-react'
import {
  fetchVehicleStaging,
  uploadVehicleFile,
  type VehicleStagingRow,
  type VehicleUploadResponse,
} from '../../api/client'
import { Button, GlassCard } from '../../components/ui/GlassCard'
import {
  DEFAULT_PAGE_SIZE,
  TablePagination,
  paginateSlice,
} from '../../components/ui/TablePagination'
import { VEHICLE_ENTITIES, type VehicleKey } from '../../data/vehicleMock'

type Phase = 'idle' | 'processing' | 'staging'

const ACCEPT =
  '.xlsx,.xls,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet,application/vnd.ms-excel'

const MAX_BYTES = 25 * 1024 * 1024

const vehicleLabel: Record<VehicleKey, string> = {
  'mutual-fund': 'Mutual Fund',
  'fixed-income': 'Fixed Income',
  'direct-equity': 'Direct Equity',
}

const jobStorageKey = (vehicle: VehicleKey) => `vehicleJob:${vehicle}`

function formatBytes(bytes: number) {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(2)} MB`
}

function formatMoney(n: number) {
  return new Intl.NumberFormat('en-IN', {
    style: 'currency',
    currency: 'INR',
    maximumFractionDigits: 2,
  }).format(n)
}

function formatUnits(n: number) {
  return new Intl.NumberFormat('en-IN', { maximumFractionDigits: 3 }).format(n)
}

function formatDate(iso: string) {
  if (!iso) return '—'
  const d = new Date(`${iso}T00:00:00`)
  if (Number.isNaN(d.getTime())) return iso
  return d.toLocaleDateString('en-IN', {
    day: '2-digit',
    month: 'short',
    year: 'numeric',
  })
}

export function VehicleUploadTab({
  vehicle,
  query: _query,
}: {
  vehicle: VehicleKey
  query: string
}) {
  const [params, setParams] = useSearchParams()
  const inputRef = useRef<HTMLInputElement | null>(null)

  const jobFromUrl = params.get('job')
  const stored = useMemo(() => {
    try {
      const raw = sessionStorage.getItem(jobStorageKey(vehicle))
      if (!raw) return null
      return JSON.parse(raw) as { jobId?: string; fileName?: string }
    } catch {
      return null
    }
  }, [vehicle])

  const initialJob = jobFromUrl || stored?.jobId || null

  const [phase, setPhase] = useState<Phase>(() => (initialJob ? 'staging' : 'idle'))
  const [entityId, setEntityId] = useState(VEHICLE_ENTITIES[0].id)
  const [jobId, setJobId] = useState<string | null>(initialJob)
  const [fileName, setFileName] = useState(stored?.fileName || '')
  const [progressLines, setProgressLines] = useState<string[]>([])
  const [error, setError] = useState<string | null>(null)
  const [rows, setRows] = useState<VehicleStagingRow[]>([])
  const [loadingRows, setLoadingRows] = useState(false)
  const [page, setPage] = useState(1)
  const [uploading, setUploading] = useState(false)

  const loadStaging = useCallback(
    async (id: string | null) => {
      setLoadingRows(true)
      setError(null)
      try {
        const data = await fetchVehicleStaging(vehicle, {
          jobId: id || undefined,
          limit: 500,
        })
        setRows(data)
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load temp transactions')
        setRows([])
      } finally {
        setLoadingRows(false)
      }
    },
    [vehicle],
  )

  useEffect(() => {
    if (phase === 'staging') {
      void loadStaging(jobId)
    }
  }, [phase, jobId, loadStaging])

  useEffect(() => {
    if (jobFromUrl && jobFromUrl !== jobId) {
      setJobId(jobFromUrl)
      setPhase('staging')
    }
  }, [jobFromUrl, jobId])

  const runUpload = async (file: File) => {
    if (uploading) return
    if (file.size === 0) {
      setError('File appears to be empty')
      return
    }
    if (file.size > MAX_BYTES) {
      setError(`Exceeds ${formatBytes(MAX_BYTES)} limit`)
      return
    }

    setUploading(true)
    setError(null)
    setPhase('processing')
    setProgressLines(['… Uploading file…'])
    setFileName(file.name)

    try {
      const result: VehicleUploadResponse = await uploadVehicleFile(file, vehicle)
      const lines = (result.steps ?? []).map((s) => {
        const mark =
          s.status === 'done' ? '✓' : s.status === 'error' ? '✗' : '…'
        return s.detail ? `${mark} ${s.label} — ${s.detail}` : `${mark} ${s.label}`
      })
      setProgressLines(lines.length ? lines : [`✓ ${result.message || 'Done'}`])

      if (result.job_id) {
        setJobId(result.job_id)
        sessionStorage.setItem(
          jobStorageKey(vehicle),
          JSON.stringify({ jobId: result.job_id, fileName: file.name }),
        )
        setParams({ tab: 'upload', job: result.job_id }, { replace: true })
      }

      if (result.status === 'failed' || result.status === 'unsupported') {
        setError(result.message || 'Import failed')
        setPhase('idle')
        return
      }

      // Brief beat so progress is readable, then show temp table
      await new Promise((r) => setTimeout(r, 500))
      setPhase('staging')
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Upload failed')
      setPhase('idle')
    } finally {
      setUploading(false)
    }
  }

  const onPick = (list: FileList | null) => {
    const file = list?.[0]
    if (file) void runUpload(file)
  }

  const resetToUpload = () => {
    sessionStorage.removeItem(jobStorageKey(vehicle))
    setJobId(null)
    setRows([])
    setProgressLines([])
    setError(null)
    setPhase('idle')
    setParams({ tab: 'upload' }, { replace: true })
  }

  const pageRows = useMemo(
    () => paginateSlice(rows, page, DEFAULT_PAGE_SIZE),
    [rows, page],
  )

  return (
    <div className="space-y-5">
      {phase === 'idle' && (
        <GlassCard className="p-4 sm:p-5" delay={0.05}>
          <div className="mb-4 max-w-sm">
            <label className="block space-y-1.5">
              <span className="text-[11px] font-semibold uppercase tracking-wider text-slate-500">
                Entity
              </span>
              <select
                value={entityId}
                onChange={(e) => setEntityId(e.target.value)}
                className="w-full rounded-xl border border-white/10 bg-navy-950/60 px-3 py-2.5 text-sm text-slate-200 outline-none focus:border-accent-400/40 focus:ring-1 focus:ring-accent-400/30"
              >
                {VEHICLE_ENTITIES.map((e) => (
                  <option key={e.id} value={e.id}>
                    {e.name}
                  </option>
                ))}
              </select>
            </label>
          </div>

          <div className="rounded-2xl border border-dashed border-white/15 bg-navy-950/40 px-6 py-14 text-center">
            <Upload className="mx-auto mb-3 h-8 w-8 text-accent-400" />
            <p className="text-sm font-semibold text-white">
              Upload {vehicleLabel[vehicle]} statement
            </p>
            <p className="mt-1 text-xs text-slate-500">
              Excel (.xls / .xlsx) · up to 25 MB · temp transactions appear after upload
            </p>
            <div className="mt-5 flex justify-center">
              <Button type="button" onClick={() => inputRef.current?.click()}>
                <FileUp className="h-4 w-4" />
                Upload file
              </Button>
            </div>
            <input
              ref={inputRef}
              type="file"
              accept={ACCEPT}
              className="hidden"
              onChange={(e) => {
                onPick(e.target.files)
                e.target.value = ''
              }}
            />
          </div>
          {error && (
            <p className="mt-3 flex items-start gap-2 text-xs text-red-300">
              <AlertCircle className="mt-0.5 h-3.5 w-3.5 shrink-0" />
              {error}
            </p>
          )}
        </GlassCard>
      )}

      {phase === 'processing' && (
        <GlassCard className="p-5" delay={0.05}>
          <div className="mb-3 flex items-center gap-2 text-sm font-semibold text-white">
            <Loader2 className="h-4 w-4 animate-spin text-cyan-300" />
            Processing {fileName || 'file'}…
          </div>
          <pre className="whitespace-pre-wrap text-xs leading-relaxed text-cyan-100/90">
            {progressLines.join('\n')}
          </pre>
        </GlassCard>
      )}

      {phase === 'staging' && (
        <>
          <GlassCard className="p-4" delay={0.05}>
            <div className="flex flex-wrap items-center justify-between gap-3">
              <div>
                <p className="text-sm font-semibold text-white">
                  Temp transactions — {vehicleLabel[vehicle]}
                </p>
                <p className="mt-0.5 text-[11px] text-slate-500">
                  {fileName ? `${fileName} · ` : ''}
                  {jobId ? `Job ${jobId}` : 'Recent staging'}
                  {rows.length ? ` · ${rows.length} row(s)` : ''}
                </p>
              </div>
              <div className="flex gap-2">
                <Button
                  type="button"
                  variant="secondary"
                  onClick={() => void loadStaging(jobId)}
                  disabled={loadingRows}
                >
                  {loadingRows ? (
                    <Loader2 className="h-4 w-4 animate-spin" />
                  ) : (
                    'Refresh'
                  )}
                </Button>
                <Button type="button" onClick={resetToUpload}>
                  <Upload className="h-4 w-4" />
                  New upload
                </Button>
              </div>
            </div>
            {progressLines.length > 0 && (
              <pre className="mt-3 whitespace-pre-wrap rounded-xl border border-white/5 bg-navy-950/50 px-3 py-2 text-[11px] text-slate-400">
                {progressLines.join('\n')}
              </pre>
            )}
            {error && (
              <p className="mt-2 text-xs text-red-300">{error}</p>
            )}
          </GlassCard>

          <GlassCard className="overflow-hidden" delay={0.1}>
            <div className="overflow-x-auto">
              <table className="w-full min-w-[920px] text-left text-sm">
                <thead>
                  <tr className="border-b border-white/5 text-[11px] uppercase tracking-wider text-slate-500">
                    <th className="px-4 py-3 font-semibold">Date</th>
                    <th className="px-3 py-3 font-semibold">Type</th>
                    <th className="px-3 py-3 font-semibold">Instrument</th>
                    <th className="px-3 py-3 font-semibold">ISIN / Folio</th>
                    <th className="px-3 py-3 font-semibold text-right">Units</th>
                    <th className="px-3 py-3 font-semibold text-right">Price</th>
                    <th className="px-3 py-3 font-semibold text-right">Amount</th>
                    <th className="px-3 py-3 font-semibold">Status</th>
                  </tr>
                </thead>
                <tbody>
                  <AnimatePresence initial={false}>
                    {pageRows.map((row, i) => (
                      <motion.tr
                        key={row.id}
                        initial={{ opacity: 0, y: 6 }}
                        animate={{ opacity: 1, y: 0 }}
                        transition={{ delay: Math.min(i, 12) * 0.02 }}
                        className="border-b border-white/[0.03] hover:bg-white/[0.02]"
                      >
                        <td className="px-4 py-3 font-mono text-xs text-slate-300">
                          {formatDate(row.tradeDate)}
                        </td>
                        <td className="px-3 py-3">
                          <span className="rounded-md bg-accent-500/15 px-2 py-0.5 text-xs text-accent-400">
                            {row.type}
                          </span>
                        </td>
                        <td className="max-w-[220px] truncate px-3 py-3 text-slate-100">
                          {row.schemeOrInstrument || '—'}
                        </td>
                        <td className="px-3 py-3 font-mono text-xs text-slate-400">
                          {row.folioOrIsin || '—'}
                        </td>
                        <td className="px-3 py-3 text-right font-mono text-xs">
                          {formatUnits(row.units)}
                        </td>
                        <td className="px-3 py-3 text-right font-mono text-xs">
                          {formatMoney(row.navOrPrice)}
                        </td>
                        <td
                          className={`px-3 py-3 text-right font-mono text-xs font-semibold ${
                            row.amount < 0 ? 'text-red-300' : 'text-green-300'
                          }`}
                        >
                          {formatMoney(row.amount)}
                        </td>
                        <td className="px-3 py-3">
                          {row.iserror ? (
                            <span className="inline-flex items-center gap-1 text-[11px] text-amber-300">
                              <AlertCircle className="h-3 w-3" />
                              Review
                            </span>
                          ) : (
                            <span className="inline-flex items-center gap-1 text-[11px] text-green-400">
                              <CheckCircle2 className="h-3 w-3" />
                              OK
                            </span>
                          )}
                        </td>
                      </motion.tr>
                    ))}
                  </AnimatePresence>
                </tbody>
              </table>
              {loadingRows && (
                <div className="flex items-center justify-center gap-2 px-5 py-16 text-sm text-slate-500">
                  <Loader2 className="h-4 w-4 animate-spin" />
                  Loading temp transactions…
                </div>
              )}
              {!loadingRows && rows.length === 0 && (
                <div className="px-5 py-16 text-center text-sm text-slate-500">
                  No temp rows yet. Upload a file with data rows, or the template was
                  header-only.
                </div>
              )}
            </div>
            <TablePagination
              page={page}
              total={rows.length}
              onPageChange={setPage}
            />
          </GlassCard>
        </>
      )}
    </div>
  )
}
