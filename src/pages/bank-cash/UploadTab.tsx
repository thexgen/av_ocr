import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { Link } from 'react-router-dom'
import { AnimatePresence, motion } from 'framer-motion'
import {
  Upload,
  FileText,
  X,
  AlertCircle,
  HardDrive,
  ArrowRight,
  FolderOpen,
  Loader2,
  Check,
  Sparkles,
  FileUp,
  ScanSearch,
  Type,
  Brain,
  ListTree,
  ShieldCheck,
  LayoutList,
  PartyPopper,
  CheckCircle2,
  AlertTriangle,
  XCircle,
  Filter,
} from 'lucide-react'
import { Button, GlassCard } from '../../components/ui/GlassCard'
import {
  DEFAULT_PAGE_SIZE,
  TablePagination,
  paginateSlice,
} from '../../components/ui/TablePagination'
import { TransactionDrawer } from '../../components/TransactionDrawer'
import { ACCEPTED_EXTENSIONS, MAX_FILE_SIZE, processingSteps } from '../../data/mockData'
import { ENTITIES } from '../../data/bankCashMock'
import {
  getJobStatus,
  getJobTransactions,
  isTerminalStatus,
  JOB_STORAGE_KEY,
  uploadHoldingFile,
  type JobStatusResponse,
  type ReviewTransaction,
} from '../../api/client'
import type { Transaction, TransactionStatus, UploadFile } from '../../types'

type Phase = 'upload' | 'processing' | 'staging'

const stepIcons = [
  FileUp,
  ScanSearch,
  FileText,
  Type,
  Brain,
  ListTree,
  ShieldCheck,
  LayoutList,
  PartyPopper,
]

const STAGE_HINTS: Record<string, number> = {
  VALIDATE_INPUT: 0,
  DETECT: 1,
  EXTRACT: 2,
  MAP: 4,
  CANONICALIZE: 5,
  NORMALIZE: 5,
  VALIDATE_ROWS: 6,
  PERSIST: 7,
  DB_STAGE: 7,
  FAILED: 8,
}

const statusMeta: Record<
  TransactionStatus,
  { label: string; row: string; badge: string; icon: typeof CheckCircle2 }
> = {
  valid: {
    label: 'Valid',
    row: 'row-valid',
    badge: 'bg-valid/15 text-green-400 border-valid/25',
    icon: CheckCircle2,
  },
  needs_review: {
    label: 'Needs Review',
    row: 'row-review',
    badge: 'bg-warning/15 text-yellow-400 border-warning/25',
    icon: AlertTriangle,
  },
  missing_data: {
    label: 'Missing Data',
    row: 'row-error',
    badge: 'bg-error/15 text-red-400 border-error/25',
    icon: XCircle,
  },
}

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

function formatNum(n: number | null) {
  if (n === null) return '—'
  return n.toLocaleString('en-US', { maximumFractionDigits: 4 })
}

function validateFile(file: File): string | null {
  const ext = `.${file.name.split('.').pop()?.toLowerCase() ?? ''}`
  if (!ACCEPTED_EXTENSIONS.includes(ext)) {
    return `Unsupported type. Allowed: ${ACCEPTED_EXTENSIONS.join(', ')}`
  }
  if (ext !== '.pdf') {
    return 'API processing currently supports PDF bank statements only'
  }
  if (file.size > MAX_FILE_SIZE) {
    return `File exceeds ${formatBytes(MAX_FILE_SIZE)} limit`
  }
  if (file.size === 0) {
    return 'File appears to be empty'
  }
  return null
}

function loadJobMeta(): { jobId: string; fileName: string } | null {
  try {
    const raw = sessionStorage.getItem(JOB_STORAGE_KEY)
    if (!raw) return null
    const parsed = JSON.parse(raw) as { jobId?: string; fileName?: string }
    if (!parsed.jobId) return null
    return {
      jobId: parsed.jobId,
      fileName: parsed.fileName || 'statement.pdf',
    }
  } catch {
    return null
  }
}

function toTransaction(row: ReviewTransaction): Transaction {
  return {
    id: row.id,
    tradeDate: row.tradeDate || '—',
    type: row.type || 'Unknown',
    security: row.security || '(no description)',
    quantity: row.quantity,
    price: row.price,
    amount: row.amount ?? 0,
    status: row.status,
    confidence: row.confidence ?? 0,
    originalText: row.originalText || row.security || '',
    normalizedJson: row.normalizedJson || {},
    validationErrors: row.validationErrors || [],
    aiReasoning: row.aiReasoning || '',
    iserror: row.iserror,
    errordesc: row.errordesc,
  }
}

export function UploadTab({ query }: { query: string }) {
  const inputRef = useRef<HTMLInputElement>(null)
  const existing = useMemo(() => loadJobMeta(), [])

  const [phase, setPhase] = useState<Phase>(() => (existing?.jobId ? 'staging' : 'upload'))
  const [entityId, setEntityId] = useState(ENTITIES[0].id)
  const [dragging, setDragging] = useState(false)
  const [files, setFiles] = useState<UploadFile[]>([])
  const [uploading, setUploading] = useState(false)
  const [uploadProgress, setUploadProgress] = useState(0)
  const [uploadError, setUploadError] = useState<string | null>(null)

  const [jobMeta, setJobMeta] = useState(existing)
  const [activeIndex, setActiveIndex] = useState(0)
  const [progress, setProgress] = useState(8)
  const [job, setJob] = useState<JobStatusResponse | null>(null)
  const [processError, setProcessError] = useState<string | null>(null)
  const [label, setLabel] = useState('Processing…')

  const [selected, setSelected] = useState<Transaction | null>(null)
  const [checked, setChecked] = useState<Set<string>>(new Set())
  const [filter, setFilter] = useState<'all' | TransactionStatus>('all')
  const [page, setPage] = useState(1)
  const [transactions, setTransactions] = useState<Transaction[]>([])
  const [stagingLoading, setStagingLoading] = useState(false)
  const [stagingError, setStagingError] = useState<string | null>(null)
  const [entityName, setEntityName] = useState(ENTITIES[0].name)
  const [fileName, setFileName] = useState(existing?.fileName ?? '')

  const addFiles = useCallback((list: FileList | File[]) => {
    const incoming = Array.from(list)
    const next: UploadFile[] = incoming.map((file) => {
      const error = validateFile(file)
      return {
        id: `${file.name}-${file.size}-${file.lastModified}-${Math.random().toString(36).slice(2, 7)}`,
        file,
        size: file.size,
        status: error ? 'error' : 'ready',
        error: error ?? undefined,
      }
    })
    setFiles((prev) => {
      const names = new Set(prev.map((f) => `${f.file.name}-${f.file.size}`))
      const unique = next.filter((f) => !names.has(`${f.file.name}-${f.file.size}`))
      return [...prev, ...unique]
    })
    setUploadError(null)
  }, [])

  const onDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault()
      setDragging(false)
      if (e.dataTransfer.files?.length) addFiles(e.dataTransfer.files)
    },
    [addFiles],
  )

  const removeFile = (id: string) => {
    setFiles((prev) => prev.filter((f) => f.id !== id))
  }

  const readyFiles = files.filter((f) => f.status === 'ready')
  const readyCount = readyFiles.length
  const totalSize = files.reduce((sum, f) => sum + f.size, 0)

  const startImport = async () => {
    if (readyCount === 0 || uploading) return
    const target = readyFiles[0]
    setUploading(true)
    setUploadProgress(0)
    setUploadError(null)

    try {
      const res = await uploadHoldingFile(target.file, setUploadProgress)
      const meta = {
        jobId: res.job_id,
        fileName: target.file.name,
      }
      sessionStorage.setItem(
        JOB_STORAGE_KEY,
        JSON.stringify({
          jobId: res.job_id,
          fileName: target.file.name,
          status: res.status,
          entityId,
          entityName: ENTITIES.find((e) => e.id === entityId)?.name,
        }),
      )
      sessionStorage.setItem('importFiles', JSON.stringify([target.file.name]))
      setJobMeta(meta)
      setFileName(target.file.name)
      setEntityName(ENTITIES.find((e) => e.id === entityId)?.name ?? 'Krishna Deval')
      setActiveIndex(0)
      setProgress(8)
      setProcessError(null)
      setPhase('processing')
      setUploading(false)
    } catch (err) {
      setUploadError(err instanceof Error ? err.message : 'Upload failed')
      setUploading(false)
    }
  }

  // Poll job while processing
  useEffect(() => {
    if (phase !== 'processing' || !jobMeta?.jobId) return

    let cancelled = false
    let timer: number | undefined

    const poll = async () => {
      try {
        const status = await getJobStatus(jobMeta.jobId)
        if (cancelled) return
        setJob(status)
        setLabel(
          status.status === 'PROCESSING' || status.status === 'QUEUED'
            ? 'Processing…'
            : status.status,
        )

        const stages = status.validation_summary?.stages ?? []
        if (stages.length > 0) {
          const last = stages[stages.length - 1]?.stage
          const idx = STAGE_HINTS[last] ?? Math.min(stages.length, processingSteps.length - 2)
          setActiveIndex(idx)
          setProgress(Math.min(95, Math.round(((idx + 1) / processingSteps.length) * 100)))
        } else if (!isTerminalStatus(status.status)) {
          setActiveIndex((i) => Math.min(i + 1, processingSteps.length - 2))
          setProgress((p) => Math.min(90, p + 8))
        }

        if (isTerminalStatus(status.status)) {
          setActiveIndex(processingSteps.length - 1)
          setProgress(100)
          sessionStorage.setItem(
            JOB_STORAGE_KEY,
            JSON.stringify({
              jobId: jobMeta.jobId,
              fileName: jobMeta.fileName,
              result: status,
            }),
          )
          window.setTimeout(() => {
            if (cancelled) return
            if (status.status === 'FAILED') {
              setProcessError(
                status.error_message ||
                  status.validation_summary?.error_message ||
                  'Extraction failed. Check the statement and try again.',
              )
            } else {
              setPhase('staging')
            }
          }, 700)
          return
        }

        timer = window.setTimeout(() => void poll(), 1200)
      } catch (err) {
        if (cancelled) return
        setProcessError(err instanceof Error ? err.message : 'Failed to poll job status')
        timer = window.setTimeout(() => void poll(), 2500)
      }
    }

    void poll()
    return () => {
      cancelled = true
      if (timer) window.clearTimeout(timer)
    }
  }, [phase, jobMeta])

  // Load staging rows
  useEffect(() => {
    if (phase !== 'staging' || !jobMeta?.jobId) return

    let cancelled = false
    const load = async () => {
      setStagingLoading(true)
      setStagingError(null)
      try {
        const data = await getJobTransactions(jobMeta.jobId)
        if (cancelled) return
        setTransactions(data.transactions.map(toTransaction))
        setEntityName(data.entity_name || ENTITIES[0].name)
        if (data.original_file_name) setFileName(data.original_file_name)
      } catch (err) {
        if (cancelled) return
        setStagingError(err instanceof Error ? err.message : 'Failed to load transactions')
      } finally {
        if (!cancelled) setStagingLoading(false)
      }
    }
    void load()
    return () => {
      cancelled = true
    }
  }, [phase, jobMeta])

  const filtered = useMemo(() => {
    return transactions.filter((t) => {
      const matchStatus = filter === 'all' || t.status === filter
      const q = query.toLowerCase()
      const matchQuery =
        !q ||
        t.security.toLowerCase().includes(q) ||
        t.type.toLowerCase().includes(q) ||
        t.tradeDate.includes(q) ||
        (t.errordesc || '').toLowerCase().includes(q)
      return matchStatus && matchQuery
    })
  }, [filter, query, transactions])

  useEffect(() => {
    setPage(1)
  }, [query, filter, transactions.length])

  const pageRows = useMemo(
    () => paginateSlice(filtered, page, DEFAULT_PAGE_SIZE),
    [filtered, page],
  )

  const allChecked = pageRows.length > 0 && pageRows.every((t) => checked.has(t.id))

  const toggleAll = () => {
    if (allChecked) {
      setChecked((prev) => {
        const next = new Set(prev)
        pageRows.forEach((t) => next.delete(t.id))
        return next
      })
    } else {
      setChecked((prev) => {
        const next = new Set(prev)
        pageRows.forEach((t) => next.add(t.id))
        return next
      })
    }
  }

  const toggleOne = (id: string) => {
    setChecked((prev) => {
      const next = new Set(prev)
      if (next.has(id)) next.delete(id)
      else next.add(id)
      return next
    })
  }

  const counts = {
    valid: transactions.filter((t) => t.status === 'valid').length,
    needs_review: transactions.filter((t) => t.status === 'needs_review').length,
    missing_data: transactions.filter((t) => t.status === 'missing_data').length,
  }

  const resetToUpload = () => {
    setPhase('upload')
    setFiles([])
    setUploadError(null)
    setProcessError(null)
    setTransactions([])
    setChecked(new Set())
    setJob(null)
    setJobMeta(null)
  }

  return (
    <div className="space-y-5">
      {/* Phase pills */}
      <div className="flex flex-wrap items-center gap-2 text-xs">
        {(
          [
            ['upload', '1. Upload'],
            ['processing', '2. Process'],
            ['staging', '3. Staging review'],
          ] as const
        ).map(([key, text]) => {
          const active = phase === key
          const done =
            (key === 'upload' && (phase === 'processing' || phase === 'staging')) ||
            (key === 'processing' && phase === 'staging')
          return (
            <span
              key={key}
              className={`rounded-full border px-3 py-1 font-semibold ${
                active
                  ? 'border-accent-400/40 bg-accent-500/20 text-accent-400'
                  : done
                    ? 'border-valid/25 bg-valid/10 text-green-400/90'
                    : 'border-white/10 text-slate-500'
              }`}
            >
              {text}
            </span>
          )
        })}
        {phase !== 'upload' && (
          <button
            type="button"
            onClick={resetToUpload}
            className="ml-auto text-xs font-semibold text-accent-400 hover:text-accent-400/80"
          >
            Upload another
          </button>
        )}
      </div>

      <AnimatePresence mode="wait">
        {phase === 'upload' && (
          <motion.div
            key="upload"
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -8 }}
            className="space-y-5"
          >
            <GlassCard className="p-4 sm:p-5" delay={0.05}>
              <label className="block max-w-sm space-y-1.5">
                <span className="text-[11px] font-semibold uppercase tracking-wider text-slate-500">
                  Entity
                </span>
                <select
                  value={entityId}
                  onChange={(e) => setEntityId(e.target.value)}
                  className="w-full rounded-xl border border-white/10 bg-navy-950/60 px-3 py-2.5 text-sm text-slate-200 outline-none focus:border-accent-400/40 focus:ring-1 focus:ring-accent-400/30"
                >
                  {ENTITIES.map((e) => (
                    <option key={e.id} value={e.id}>
                      {e.name}
                    </option>
                  ))}
                </select>
              </label>
            </GlassCard>

            <GlassCard strong delay={0.08} className="overflow-hidden">
              <div
                onDragOver={(e) => {
                  e.preventDefault()
                  setDragging(true)
                }}
                onDragLeave={() => setDragging(false)}
                onDrop={onDrop}
                className={`relative m-4 rounded-2xl border-2 border-dashed transition-all duration-300 ${
                  dragging
                    ? 'border-accent-400 bg-accent-500/10 glow-pulse'
                    : 'border-accent-400/25 bg-navy-900/40 hover:border-accent-400/45 hover:bg-accent-500/5'
                }`}
              >
                <div className="flex flex-col items-center px-6 py-14 text-center">
                  <motion.div
                    animate={dragging ? { scale: 1.08, y: -4 } : { scale: 1, y: 0 }}
                    className={`mb-5 flex h-16 w-16 items-center justify-center rounded-2xl border ${
                      dragging
                        ? 'border-accent-400/40 bg-accent-500/20 glow-blue'
                        : 'border-accent-400/20 bg-accent-500/10'
                    }`}
                  >
                    <Upload
                      className={`h-7 w-7 ${dragging ? 'text-accent-400' : 'text-accent-400/80'}`}
                    />
                  </motion.div>

                  <p className="text-lg font-bold text-white">
                    {dragging ? 'Drop files to upload' : 'Drag & drop bank statements here'}
                  </p>
                  <p className="mt-1.5 max-w-sm text-sm text-slate-400">
                    PDF bank statements up to {formatBytes(MAX_FILE_SIZE)}. Rows stage into{' '}
                    <span className="text-slate-300">bankcashtemp</span>.
                  </p>

                  <div className="mt-6 flex flex-wrap items-center justify-center gap-3">
                    <Button
                      variant="secondary"
                      icon={FolderOpen}
                      disabled={uploading}
                      onClick={() => inputRef.current?.click()}
                    >
                      Browse Files
                    </Button>
                    <span className="text-xs text-slate-500">or drop anywhere in this zone</span>
                  </div>

                  <input
                    ref={inputRef}
                    type="file"
                    accept=".pdf,application/pdf"
                    className="hidden"
                    onChange={(e) => {
                      if (e.target.files?.length) addFiles(e.target.files)
                      e.target.value = ''
                    }}
                  />
                </div>
              </div>
            </GlassCard>

            <AnimatePresence mode="popLayout">
              {files.length > 0 && (
                <motion.div
                  initial={{ opacity: 0, y: 12 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, y: -8 }}
                >
                  <GlassCard className="overflow-hidden" delay={0}>
                    <div className="flex flex-wrap items-center justify-between gap-3 border-b border-white/5 px-5 py-4">
                      <div>
                        <h2 className="text-sm font-bold text-white">Upload Queue</h2>
                        <p className="text-xs text-slate-500">
                          {readyCount} ready · {files.length - readyCount} invalid ·{' '}
                          {formatBytes(totalSize)} total
                        </p>
                      </div>
                      <div className="flex items-center gap-2 text-xs text-slate-400">
                        <HardDrive className="h-3.5 w-3.5" />
                        Capacity check passed
                      </div>
                    </div>

                    <ul className="divide-y divide-white/5">
                      <AnimatePresence initial={false}>
                        {files.map((item) => (
                          <motion.li
                            key={item.id}
                            layout
                            initial={{ opacity: 0, height: 0 }}
                            animate={{ opacity: 1, height: 'auto' }}
                            exit={{ opacity: 0, height: 0, x: 40 }}
                            transition={{ duration: 0.25 }}
                            className="overflow-hidden"
                          >
                            <div className="flex items-center gap-3 px-5 py-3.5">
                              <div
                                className={`flex h-10 w-10 shrink-0 items-center justify-center rounded-xl border ${
                                  item.status === 'error'
                                    ? 'border-error/30 bg-error/10'
                                    : 'border-accent-400/20 bg-accent-500/10'
                                }`}
                              >
                                {item.status === 'error' ? (
                                  <AlertCircle className="h-4 w-4 text-red-400" />
                                ) : (
                                  <FileText className="h-4 w-4 text-accent-400" />
                                )}
                              </div>

                              <div className="min-w-0 flex-1">
                                <p className="truncate text-sm font-semibold text-slate-100">
                                  {item.file.name}
                                </p>
                                {item.error ? (
                                  <p className="text-xs text-red-400">{item.error}</p>
                                ) : (
                                  <div className="mt-1.5">
                                    <div className="mb-1 flex justify-between text-[10px] text-slate-500">
                                      <span>{formatBytes(item.size)}</span>
                                      <span>
                                        {((item.size / MAX_FILE_SIZE) * 100).toFixed(1)}% of
                                        limit
                                      </span>
                                    </div>
                                    <div className="h-1.5 overflow-hidden rounded-full bg-navy-700">
                                      <motion.div
                                        initial={{ width: 0 }}
                                        animate={{
                                          width: `${Math.min(100, (item.size / MAX_FILE_SIZE) * 100)}%`,
                                        }}
                                        transition={{ duration: 0.6, ease: 'easeOut' }}
                                        className="h-full rounded-full bg-gradient-to-r from-accent-600 to-accent-400"
                                      />
                                    </div>
                                  </div>
                                )}
                              </div>

                              <button
                                type="button"
                                disabled={uploading}
                                onClick={() => removeFile(item.id)}
                                className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg text-slate-500 transition-colors hover:bg-error/15 hover:text-red-400 disabled:opacity-40"
                                aria-label="Remove file"
                              >
                                <X className="h-4 w-4" />
                              </button>
                            </div>
                          </motion.li>
                        ))}
                      </AnimatePresence>
                    </ul>

                    {uploading && (
                      <div className="border-t border-white/5 px-5 py-4">
                        <div className="mb-2 flex items-center justify-between text-xs">
                          <span className="inline-flex items-center gap-2 font-medium text-accent-400">
                            <Loader2 className="h-3.5 w-3.5 animate-spin" />
                            Uploading to processing engine…
                          </span>
                          <span className="font-mono text-accent-400">{uploadProgress}%</span>
                        </div>
                        <div className="h-2 overflow-hidden rounded-full bg-navy-700">
                          <motion.div
                            className="h-full rounded-full bg-gradient-to-r from-accent-600 to-accent-400"
                            animate={{ width: `${uploadProgress}%` }}
                          />
                        </div>
                      </div>
                    )}

                    {uploadError && (
                      <div className="border-t border-error/20 bg-error/10 px-5 py-3 text-sm text-red-300">
                        {uploadError}
                      </div>
                    )}

                    <div className="flex flex-col-reverse gap-3 border-t border-white/5 px-5 py-4 sm:flex-row sm:justify-end">
                      <Button
                        variant="ghost"
                        disabled={uploading}
                        onClick={() => {
                          setFiles([])
                          setUploadError(null)
                        }}
                      >
                        Clear All
                      </Button>
                      <Button
                        icon={uploading ? Loader2 : ArrowRight}
                        disabled={readyCount === 0 || uploading}
                        onClick={() => void startImport()}
                      >
                        {uploading
                          ? 'Uploading…'
                          : `Start AI Import (${Math.min(readyCount, 1)})`}
                      </Button>
                    </div>
                  </GlassCard>
                </motion.div>
              )}
            </AnimatePresence>
          </motion.div>
        )}

        {phase === 'processing' && (
          <motion.div
            key="processing"
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -8 }}
            className="mx-auto max-w-2xl space-y-6"
          >
            <div className="text-center">
              <motion.div
                initial={{ scale: 0.8, opacity: 0 }}
                animate={{ scale: 1, opacity: 1 }}
                className="mx-auto mb-5 flex h-16 w-16 items-center justify-center rounded-2xl border border-accent-400/30 bg-accent-500/15 glow-pulse"
              >
                <Sparkles className="h-7 w-7 text-accent-400" />
              </motion.div>
              <h2 className="text-xl font-extrabold tracking-tight text-white sm:text-2xl">
                {label}
              </h2>
              <p className="mt-2 text-sm text-slate-400">
                Analyzing{' '}
                <span className="font-medium text-accent-400">
                  {jobMeta?.fileName ?? 'statement.pdf'}
                </span>
                {jobMeta?.jobId && (
                  <>
                    {' '}
                    · <span className="font-mono text-xs text-slate-500">{jobMeta.jobId}</span>
                  </>
                )}
              </p>
            </div>

            {processError && (
              <div className="space-y-3">
                <div className="flex items-start gap-2 rounded-xl border border-error/30 bg-error/10 px-4 py-3 text-sm text-red-300">
                  <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" />
                  {processError}
                </div>
                <Button variant="secondary" onClick={resetToUpload}>
                  Back to upload
                </Button>
              </div>
            )}

            <GlassCard strong className="p-6" delay={0.05}>
              <div className="mb-2 flex items-center justify-between text-xs">
                <span className="font-medium text-slate-400">Overall Progress</span>
                <span className="font-mono font-semibold text-accent-400">
                  {Math.round(progress)}%
                </span>
              </div>
              <div className="h-2.5 overflow-hidden rounded-full bg-navy-700">
                <motion.div
                  className="relative h-full rounded-full bg-gradient-to-r from-accent-700 via-accent-500 to-accent-400"
                  style={{ width: `${progress}%` }}
                  transition={{ duration: 0.15 }}
                >
                  <div className="absolute inset-0 shimmer opacity-60" />
                </motion.div>
              </div>
              {job?.status && (
                <p className="mt-3 text-xs text-slate-500">
                  Engine status: <span className="text-slate-300">{job.status}</span>
                </p>
              )}
            </GlassCard>

            <GlassCard className="overflow-hidden p-2" delay={0.1}>
              <ul className="space-y-1 p-2">
                {processingSteps.map((step, index) => {
                  const Icon = stepIcons[index]
                  const done = index < activeIndex
                  const active = index === activeIndex
                  const pending = index > activeIndex

                  return (
                    <motion.li
                      key={step.id}
                      layout
                      className={`relative overflow-hidden rounded-xl px-4 py-3.5 transition-colors ${
                        active
                          ? 'bg-accent-500/10 border border-accent-400/25'
                          : done
                            ? 'bg-valid/5 border border-transparent'
                            : 'border border-transparent'
                      }`}
                    >
                      {active && (
                        <motion.div
                          layoutId="step-glow-inline"
                          className="pointer-events-none absolute inset-0 bg-gradient-to-r from-accent-500/5 via-accent-400/10 to-transparent"
                        />
                      )}

                      <div className="relative flex items-start gap-3.5">
                        <div
                          className={`mt-0.5 flex h-9 w-9 shrink-0 items-center justify-center rounded-xl border transition-all ${
                            done
                              ? 'border-valid/40 bg-valid/15 text-green-400'
                              : active
                                ? 'border-accent-400/40 bg-accent-500/20 text-accent-400 glow-blue'
                                : 'border-white/10 bg-navy-800 text-slate-500'
                          }`}
                        >
                          <AnimatePresence mode="wait">
                            {done ? (
                              <motion.span
                                key="check"
                                initial={{ scale: 0 }}
                                animate={{ scale: 1 }}
                                exit={{ scale: 0 }}
                              >
                                <Check className="h-4 w-4" strokeWidth={2.5} />
                              </motion.span>
                            ) : active ? (
                              <motion.span
                                key="loader"
                                initial={{ opacity: 0 }}
                                animate={{ opacity: 1 }}
                              >
                                <Loader2 className="h-4 w-4 animate-spin" />
                              </motion.span>
                            ) : (
                              <Icon className="h-4 w-4" />
                            )}
                          </AnimatePresence>
                        </div>

                        <div className="min-w-0 flex-1">
                          <div className="flex items-center justify-between gap-2">
                            <p
                              className={`text-sm font-semibold ${
                                pending ? 'text-slate-500' : 'text-slate-100'
                              }`}
                            >
                              {step.label}
                            </p>
                            {done && (
                              <span className="text-[11px] font-medium text-green-400/80">
                                Done
                              </span>
                            )}
                            {active && (
                              <span className="text-[11px] font-medium text-accent-400">
                                Processing…
                              </span>
                            )}
                          </div>
                          <p
                            className={`mt-0.5 text-xs ${
                              pending ? 'text-slate-600' : 'text-slate-500'
                            }`}
                          >
                            {step.description}
                          </p>
                        </div>
                      </div>
                    </motion.li>
                  )
                })}
              </ul>
            </GlassCard>
          </motion.div>
        )}

        {phase === 'staging' && (
          <motion.div
            key="staging"
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -8 }}
            className="space-y-5"
          >
            <div className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
              <div>
                <h2 className="text-lg font-bold text-white">Staging review</h2>
                <p className="mt-1 text-sm text-slate-400">
                  Staged in <span className="text-slate-300">bankcashtemp</span>
                  {fileName ? (
                    <>
                      {' '}
                      · <span className="font-medium text-accent-400">{fileName}</span>
                    </>
                  ) : null}
                  {' '}
                  · Entity: <span className="text-slate-300">{entityName}</span>
                  {jobMeta?.jobId ? (
                    <>
                      {' '}
                      ·{' '}
                      <span className="font-mono text-xs text-slate-500">{jobMeta.jobId}</span>
                    </>
                  ) : null}
                </p>
              </div>
              <Link to="/success">
                <Button icon={ArrowRight}>
                  Confirm Import ({checked.size || filtered.length})
                </Button>
              </Link>
            </div>

            {stagingError && (
              <div className="flex items-start gap-2 rounded-xl border border-error/30 bg-error/10 px-4 py-3 text-sm text-red-300">
                <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" />
                <div>
                  <p>{stagingError}</p>
                  <button
                    type="button"
                    onClick={resetToUpload}
                    className="mt-1 text-accent-400 underline"
                  >
                    Upload again
                  </button>
                </div>
              </div>
            )}

            <div className="flex flex-wrap gap-2">
              {(
                [
                  ['all', `All (${transactions.length})`],
                  ['valid', `Valid (${counts.valid})`],
                  ['needs_review', `Needs Review (${counts.needs_review})`],
                  ['missing_data', `Missing Data (${counts.missing_data})`],
                ] as const
              ).map(([key, text]) => (
                <button
                  key={key}
                  type="button"
                  onClick={() => setFilter(key)}
                  className={`rounded-full border px-3 py-1.5 text-xs font-semibold transition-all ${
                    filter === key
                      ? 'border-accent-400/40 bg-accent-500/20 text-accent-400'
                      : 'border-white/10 bg-white/[0.02] text-slate-400 hover:border-white/20 hover:text-slate-200'
                  }`}
                >
                  {text}
                </button>
              ))}
            </div>

            <GlassCard className="overflow-hidden" delay={0.08}>
              <div className="flex items-center justify-between border-b border-white/5 px-4 py-3">
                <div className="flex items-center gap-2 text-xs text-slate-500">
                  {stagingLoading ? (
                    <>
                      <Loader2 className="h-3.5 w-3.5 animate-spin" /> Loading from MySQL…
                    </>
                  ) : (
                    <>
                      <Filter className="h-3.5 w-3.5" />
                      {filtered.length} rows · click a row for detail
                    </>
                  )}
                </div>
              </div>

              <div className="overflow-x-auto">
                <table className="w-full min-w-[900px] text-left text-sm">
                  <thead>
                    <tr className="border-b border-white/5 text-[11px] uppercase tracking-wider text-slate-500">
                      <th className="px-4 py-3 font-semibold">
                        <input
                          type="checkbox"
                          checked={allChecked}
                          onChange={toggleAll}
                          className="h-3.5 w-3.5 rounded border-slate-600 bg-navy-800 accent-accent-500"
                          aria-label="Select all"
                        />
                      </th>
                      <th className="px-3 py-3 font-semibold">Trade Date</th>
                      <th className="px-3 py-3 font-semibold">Type</th>
                      <th className="px-3 py-3 font-semibold">Description</th>
                      <th className="px-3 py-3 font-semibold text-right">Quantity</th>
                      <th className="px-3 py-3 font-semibold text-right">Price</th>
                      <th className="px-3 py-3 font-semibold text-right">Amount</th>
                      <th className="px-3 py-3 font-semibold">Status</th>
                      <th className="px-3 py-3 font-semibold">Errors</th>
                    </tr>
                  </thead>
                  <tbody>
                    {!stagingLoading &&
                      pageRows.map((txn, i) => {
                        const metaRow = statusMeta[txn.status]
                        const StatusIcon = metaRow.icon
                        return (
                          <motion.tr
                            key={txn.id}
                            initial={{ opacity: 0, y: 6 }}
                            animate={{ opacity: 1, y: 0 }}
                            transition={{ delay: Math.min(i, 20) * 0.02 }}
                            onClick={() => setSelected(txn)}
                            className={`cursor-pointer border-b border-white/[0.03] transition-colors ${metaRow.row}`}
                          >
                            <td
                              className="px-4 py-3"
                              onClick={(e) => e.stopPropagation()}
                            >
                              <input
                                type="checkbox"
                                checked={checked.has(txn.id)}
                                onChange={() => toggleOne(txn.id)}
                                className="h-3.5 w-3.5 rounded border-slate-600 bg-navy-800 accent-accent-500"
                                aria-label={`Select ${txn.id}`}
                              />
                            </td>
                            <td className="px-3 py-3 font-mono text-xs text-slate-300">
                              {txn.tradeDate || '—'}
                            </td>
                            <td className="px-3 py-3">
                              <span className="rounded-md bg-navy-700/80 px-2 py-0.5 text-xs font-medium text-slate-300">
                                {txn.type}
                              </span>
                            </td>
                            <td className="max-w-[260px] truncate px-3 py-3 font-medium text-slate-100">
                              {txn.security}
                            </td>
                            <td className="px-3 py-3 text-right font-mono text-xs text-slate-300">
                              {formatNum(txn.quantity)}
                            </td>
                            <td className="px-3 py-3 text-right font-mono text-xs text-slate-300">
                              {txn.price !== null ? formatMoney(txn.price) : '—'}
                            </td>
                            <td
                              className={`px-3 py-3 text-right font-mono text-xs font-semibold ${
                                txn.amount < 0 ? 'text-red-300' : 'text-green-300'
                              }`}
                            >
                              {formatMoney(txn.amount)}
                            </td>
                            <td className="px-3 py-3">
                              <span
                                className={`inline-flex items-center gap-1 rounded-full border px-2 py-0.5 text-[11px] font-semibold ${metaRow.badge}`}
                              >
                                <StatusIcon className="h-3 w-3" />
                                {metaRow.label}
                              </span>
                            </td>
                            <td className="max-w-[200px] truncate px-3 py-3 text-xs text-red-300/90">
                              {txn.errordesc || '—'}
                            </td>
                          </motion.tr>
                        )
                      })}
                  </tbody>
                </table>

                {stagingLoading && (
                  <div className="flex items-center justify-center gap-2 px-5 py-16 text-sm text-slate-500">
                    <Loader2 className="h-4 w-4 animate-spin" />
                    Loading transactions from bankcashtemp…
                  </div>
                )}

                {!stagingLoading && filtered.length === 0 && !stagingError && (
                  <div className="px-5 py-16 text-center text-sm text-slate-500">
                    No transactions match your filters.
                  </div>
                )}
              </div>

              {!stagingLoading && (
                <TablePagination
                  page={page}
                  total={filtered.length}
                  onPageChange={setPage}
                />
              )}
            </GlassCard>

            <TransactionDrawer
              transaction={selected}
              onClose={() => setSelected(null)}
            />
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}
