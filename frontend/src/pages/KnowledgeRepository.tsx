import { useRef, useState, type ChangeEvent, type DragEvent } from 'react'
import {
  CheckCircle2,
  FileText,
  Loader2,
  Trash2,
  Upload,
  XCircle,
} from 'lucide-react'
import { GlassCard, Button, StatCard } from '../components/ui/GlassCard'
import { useKnowledgeRepository } from '../features/jessy/knowledge-repository/useKnowledgeRepository'

export function KnowledgeRepositoryPage() {
  const {
    documents,
    stats,
    addDocuments,
    deleteDocument,
    uploading,
    notification,
  } = useKnowledgeRepository()
  const [isDragging, setIsDragging] = useState(false)
  const fileInputRef = useRef<HTMLInputElement | null>(null)

  const handleFiles = (files: FileList | null) => {
    if (uploading) return
    void addDocuments(files)
  }

  const handleDrop = (event: DragEvent<HTMLDivElement>) => {
    event.preventDefault()
    if (uploading) return
    setIsDragging(false)
    handleFiles(event.dataTransfer.files)
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <p className="text-xs font-semibold uppercase tracking-wider text-accent-400">
            Settings · Admin
          </p>
          <h1 className="mt-1 text-2xl font-bold tracking-tight text-white sm:text-3xl">
            Knowledge Repository
          </h1>
          <p className="mt-2 max-w-xl text-sm text-slate-400">
            Upload PDFs that power Jessy&apos;s RAG answers. Pipeline: extract →
            chunk → embed → Qdrant.
          </p>
        </div>
        <Button
          onClick={() => fileInputRef.current?.click()}
          disabled={uploading}
          icon={Upload}
        >
          {uploading ? 'Uploading...' : 'Browse Files'}
        </Button>
      </div>

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard label="Total Documents" value={String(stats.total)} icon={FileText} delay={0} />
        <StatCard
          label="Ready"
          value={String(stats.ready)}
          icon={CheckCircle2}
          accent="from-valid/20 to-valid/5"
          delay={0.05}
        />
        <StatCard
          label="Processing"
          value={String(stats.processing)}
          icon={Loader2}
          accent="from-warning/20 to-warning/5"
          delay={0.1}
        />
        <StatCard
          label="Failed"
          value={String(stats.failed)}
          icon={XCircle}
          accent="from-error/20 to-error/5"
          delay={0.15}
        />
      </div>

      <GlassCard
        className={`border-dashed p-8 text-center transition-colors ${
          isDragging ? 'border-accent-400/50 bg-accent-500/10' : ''
        }`}
      >
        <div
          onDragOver={(event) => {
            event.preventDefault()
            setIsDragging(true)
          }}
          onDragLeave={() => setIsDragging(false)}
          onDrop={handleDrop}
          className="flex flex-col items-center"
        >
          <input
            ref={fileInputRef}
            type="file"
            accept=".pdf"
            multiple
            hidden
            disabled={uploading}
            onChange={(event: ChangeEvent<HTMLInputElement>) =>
              handleFiles(event.target.files)
            }
          />
          <div className="mb-4 flex h-14 w-14 items-center justify-center rounded-2xl border border-accent-400/20 bg-accent-500/10">
            <Upload className="h-6 w-6 text-accent-400" />
          </div>
          <h2 className="text-lg font-semibold text-white">
            {uploading ? 'Uploading...' : 'Drop PDF files here'}
          </h2>
          <p className="mt-1 text-sm text-slate-400">
            {uploading
              ? 'Please wait until the upload finishes.'
              : 'or use Browse Files to add documents for Jessy.'}
          </p>
        </div>
      </GlassCard>

      <GlassCard className="overflow-hidden">
        <div className="flex items-center justify-between border-b border-white/5 px-5 py-4">
          <h3 className="text-sm font-semibold text-white">Uploaded Documents</h3>
          <span className="text-xs text-slate-500">{documents.length} files</span>
        </div>

        {notification && (
          <div className="border-b border-white/5 px-5 py-3 text-sm text-slate-300">
            {notification}
          </div>
        )}

        <div className="overflow-x-auto">
          <table className="w-full min-w-[560px] text-left text-sm">
            <thead>
              <tr className="border-b border-white/5 text-xs uppercase tracking-wider text-slate-500">
                <th className="px-5 py-3 font-medium">File Name</th>
                <th className="px-5 py-3 font-medium">Upload Date</th>
                <th className="px-5 py-3 font-medium">Status</th>
                <th className="px-5 py-3 font-medium">Action</th>
              </tr>
            </thead>
            <tbody>
              {documents.length === 0 ? (
                <tr>
                  <td colSpan={4} className="px-5 py-10 text-center text-slate-500">
                    No documents yet. Upload a PDF to get started.
                  </td>
                </tr>
              ) : (
                documents.map((document) => (
                  <tr
                    key={document.id}
                    className="border-b border-white/[0.04] last:border-0"
                  >
                    <td className="px-5 py-3.5 font-medium text-slate-200">
                      {document.name}
                    </td>
                    <td className="px-5 py-3.5 text-slate-400">{document.uploadDate}</td>
                    <td className="px-5 py-3.5">
                      <StatusPill status={document.status} />
                    </td>
                    <td className="px-5 py-3.5">
                      <button
                        type="button"
                        onClick={() => deleteDocument(document.id)}
                        className="inline-flex items-center gap-1.5 rounded-lg px-2 py-1 text-xs text-red-300 transition hover:bg-error/15"
                      >
                        <Trash2 className="h-3.5 w-3.5" />
                        Delete
                      </button>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </GlassCard>
    </div>
  )
}

function StatusPill({ status }: { status: string }) {
  const styles =
    status === 'Ready'
      ? 'border-valid/30 bg-valid/10 text-green-300'
      : status === 'Processing'
        ? 'border-warning/30 bg-warning/10 text-yellow-200'
        : 'border-error/30 bg-error/10 text-red-300'

  return (
    <span
      className={`inline-flex rounded-md border px-2 py-0.5 text-[11px] font-semibold uppercase tracking-wide ${styles}`}
    >
      {status}
    </span>
  )
}
