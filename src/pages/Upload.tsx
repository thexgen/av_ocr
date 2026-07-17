import { useCallback, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
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
} from 'lucide-react'
import { Button, GlassCard } from '../components/ui/GlassCard'
import {
  ACCEPTED_EXTENSIONS,
  MAX_FILE_SIZE,
} from '../data/mockData'
import { JOB_STORAGE_KEY, uploadHoldingFile } from '../api/client'
import type { UploadFile } from '../types'

function formatBytes(bytes: number) {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(2)} MB`
}

function validateFile(file: File): string | null {
  const ext = `.${file.name.split('.').pop()?.toLowerCase() ?? ''}`
  if (!ACCEPTED_EXTENSIONS.includes(ext)) {
    return `Unsupported type. Allowed: ${ACCEPTED_EXTENSIONS.join(', ')}`
  }
  // Engine currently accepts PDF only
  if (ext !== '.pdf') {
    return 'API processing currently supports PDF holdings only'
  }
  if (file.size > MAX_FILE_SIZE) {
    return `File exceeds ${formatBytes(MAX_FILE_SIZE)} limit`
  }
  if (file.size === 0) {
    return 'File appears to be empty'
  }
  return null
}

export function UploadPage() {
  const navigate = useNavigate()
  const inputRef = useRef<HTMLInputElement>(null)
  const [dragging, setDragging] = useState(false)
  const [files, setFiles] = useState<UploadFile[]>([])
  const [uploading, setUploading] = useState(false)
  const [uploadProgress, setUploadProgress] = useState(0)
  const [uploadError, setUploadError] = useState<string | null>(null)

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
      sessionStorage.setItem(
        JOB_STORAGE_KEY,
        JSON.stringify({
          jobId: res.job_id,
          fileName: target.file.name,
          status: res.status,
        }),
      )
      sessionStorage.setItem('importFiles', JSON.stringify([target.file.name]))
      navigate('/processing')
    } catch (err) {
      setUploadError(err instanceof Error ? err.message : 'Upload failed')
      setUploading(false)
    }
  }

  return (
    <div className="mx-auto max-w-3xl space-y-6">
      <div>
        <h1 className="text-2xl font-extrabold tracking-tight text-white sm:text-3xl">
          Upload Statements
        </h1>
        <p className="mt-1.5 text-sm text-slate-400">
          Drag and drop a holding statement PDF to begin AI extraction.
        </p>
      </div>

      <GlassCard strong delay={0.05} className="overflow-hidden">
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
              {dragging ? 'Drop files to upload' : 'Drag & drop statements here'}
            </p>
            <p className="mt-1.5 max-w-sm text-sm text-slate-400">
              PDF holdings up to {formatBytes(MAX_FILE_SIZE)}. Connected to local
              processing API.
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
    </div>
  )
}
