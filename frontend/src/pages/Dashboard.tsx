import { Link } from 'react-router-dom'
import { motion } from 'framer-motion'
import {
  Upload,
  FileText,
  FileSpreadsheet,
  Activity,
  CheckCircle2,
  AlertTriangle,
  Clock,
  TrendingUp,
  Sparkles,
  Files,
  BarChart3,
  ShieldCheck,
} from 'lucide-react'
import { Button, GlassCard, StatCard } from '../components/ui/GlassCard'
import {
  importStats,
  recentImports,
  supportedFileTypes,
} from '../data/mockData'

const statusConfig = {
  completed: {
    label: 'Completed',
    className: 'bg-valid/15 text-green-400 border-valid/25',
    icon: CheckCircle2,
  },
  processing: {
    label: 'Processing',
    className: 'bg-accent-500/15 text-accent-400 border-accent-400/25',
    icon: Activity,
  },
  review: {
    label: 'Needs Review',
    className: 'bg-warning/15 text-yellow-400 border-warning/25',
    icon: AlertTriangle,
  },
  failed: {
    label: 'Failed',
    className: 'bg-error/15 text-red-400 border-error/25',
    icon: AlertTriangle,
  },
}

const typeIcons: Record<string, typeof FileText> = {
  PDF: FileText,
  CSV: FileSpreadsheet,
  XLSX: FileSpreadsheet,
  OFX: Files,
}

function formatDate(iso: string) {
  return new Date(iso).toLocaleString('en-US', {
    month: 'short',
    day: 'numeric',
    hour: 'numeric',
    minute: '2-digit',
  })
}

export function Dashboard() {
  return (
    <div className="space-y-8">
      {/* Hero */}
      <div className="flex flex-col gap-6 lg:flex-row lg:items-end lg:justify-between">
        <motion.div
          initial={{ opacity: 0, x: -16 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ duration: 0.5 }}
        >
          <div className="mb-3 inline-flex items-center gap-2 rounded-full border border-accent-400/20 bg-accent-500/10 px-3 py-1 text-xs font-medium text-accent-400">
            <Sparkles className="h-3.5 w-3.5" />
            Intelligent Document Pipeline
          </div>
          <h1 className="text-3xl font-extrabold tracking-tight text-white sm:text-4xl">
            AI Statement Import
          </h1>
          <p className="mt-2 max-w-xl text-sm leading-relaxed text-slate-400 sm:text-base">
            Upload brokerage statements and let AI extract, normalize, and
            validate investment transactions for analyst review.
          </p>
        </motion.div>

        <Link to="/transactions/bank-cash?tab=upload">
          <Button size="lg" icon={Upload} className="w-full sm:w-auto">
            Upload Bank Statement
          </Button>
        </Link>
      </div>

      {/* Stats */}
      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <StatCard
          label="Total Imports"
          value={importStats.totalImports.toLocaleString()}
          sub="Last 90 days"
          icon={BarChart3}
          delay={0.05}
        />
        <StatCard
          label="Transactions Extracted"
          value={importStats.transactionsExtracted.toLocaleString()}
          sub="+1,284 this week"
          icon={TrendingUp}
          accent="from-emerald-500/20 to-emerald-700/10"
          delay={0.1}
        />
        <StatCard
          label="Avg Confidence"
          value={`${importStats.avgConfidence}%`}
          sub="Model accuracy"
          icon={ShieldCheck}
          accent="from-sky-500/20 to-sky-700/10"
          delay={0.15}
        />
        <StatCard
          label="Pending Review"
          value={String(importStats.pendingReview)}
          sub="Requires analyst action"
          icon={Clock}
          accent="from-amber-500/20 to-amber-700/10"
          delay={0.2}
        />
      </div>

      <div className="grid gap-6 lg:grid-cols-5">
        {/* Recent imports */}
        <GlassCard className="lg:col-span-3 overflow-hidden" delay={0.15}>
          <div className="flex items-center justify-between border-b border-white/5 px-5 py-4">
            <div>
              <h2 className="text-base font-bold text-white">Recent Imports</h2>
              <p className="text-xs text-slate-500">Latest statement processing activity</p>
            </div>
            <Link
              to="/transactions/bank-cash"
              className="text-xs font-semibold text-accent-400 hover:text-accent-400/80"
            >
              Bank Cash
            </Link>
          </div>

          <div className="divide-y divide-white/5">
            {recentImports.map((item, i) => {
              const cfg = statusConfig[item.status]
              const StatusIcon = cfg.icon
              return (
                <motion.div
                  key={item.id}
                  initial={{ opacity: 0, x: -8 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ delay: 0.2 + i * 0.05 }}
                  className="flex items-center gap-4 px-5 py-3.5 transition-colors hover:bg-white/[0.02]"
                >
                  <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-accent-500/10 border border-accent-400/15">
                    <FileText className="h-4.5 w-4.5 text-accent-400" />
                  </div>
                  <div className="min-w-0 flex-1">
                    <p className="truncate text-sm font-semibold text-slate-100">
                      {item.fileName}
                    </p>
                    <p className="text-xs text-slate-500">
                      {item.broker} · {formatDate(item.uploadedAt)}
                    </p>
                  </div>
                  <div className="hidden text-right sm:block">
                    <p className="text-sm font-medium text-slate-300">
                      {item.transactionCount}
                    </p>
                    <p className="text-[10px] uppercase tracking-wide text-slate-500">
                      txns
                    </p>
                  </div>
                  <span
                    className={`inline-flex items-center gap-1 rounded-full border px-2.5 py-1 text-[11px] font-semibold ${cfg.className}`}
                  >
                    <StatusIcon className="h-3 w-3" />
                    {cfg.label}
                  </span>
                </motion.div>
              )
            })}
          </div>
        </GlassCard>

        {/* Supported types */}
        <GlassCard className="lg:col-span-2 p-5" delay={0.25}>
          <h2 className="text-base font-bold text-white">Supported File Types</h2>
          <p className="mt-1 text-xs text-slate-500">
            Secure intake for major brokerage formats
          </p>

          <div className="mt-5 space-y-3">
            {supportedFileTypes.map((type, i) => {
              const Icon = typeIcons[type.ext] ?? FileText
              return (
                <motion.div
                  key={type.ext}
                  initial={{ opacity: 0, y: 8 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: 0.3 + i * 0.06 }}
                  className="flex items-center gap-3 rounded-xl border border-white/5 bg-white/[0.02] px-3.5 py-3 transition-colors hover:border-accent-400/20"
                >
                  <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-accent-500/10">
                    <Icon className="h-4 w-3.5 text-accent-400" />
                  </div>
                  <div className="flex-1">
                    <p className="text-sm font-semibold text-slate-200">
                      {type.label}
                    </p>
                    <p className="text-[11px] text-slate-500">
                      Max {type.maxSize}
                    </p>
                  </div>
                  <span className="rounded-md bg-navy-700 px-2 py-0.5 font-mono text-[10px] font-medium text-accent-400">
                    .{type.ext.toLowerCase()}
                  </span>
                </motion.div>
              )
            })}
          </div>

          <div className="mt-5 rounded-xl border border-accent-400/15 bg-accent-500/5 p-3.5">
            <p className="text-xs leading-relaxed text-slate-400">
              Files are processed locally in this demo using mock AI extraction.
              No data leaves your browser.
            </p>
          </div>
        </GlassCard>
      </div>
    </div>
  )
}
