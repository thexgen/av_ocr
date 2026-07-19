import { motion } from 'framer-motion'
import type { LucideIcon } from 'lucide-react'
import type { ReactNode } from 'react'

interface GlassCardProps {
  children: ReactNode
  className?: string
  hover?: boolean
  strong?: boolean
  delay?: number
}

export function GlassCard({
  children,
  className = '',
  hover = false,
  strong = false,
  delay = 0,
}: GlassCardProps) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.45, delay, ease: [0.22, 1, 0.36, 1] }}
      className={`rounded-2xl ${strong ? 'glass-strong' : 'glass'} ${
        hover ? 'glass-hover transition-all duration-300' : ''
      } ${className}`}
    >
      {children}
    </motion.div>
  )
}

interface StatCardProps {
  label: string
  value: string
  sub?: string
  icon: LucideIcon
  accent?: string
  delay?: number
}

export function StatCard({
  label,
  value,
  sub,
  icon: Icon,
  accent = 'from-accent-500/20 to-accent-700/10',
  delay = 0,
}: StatCardProps) {
  return (
    <GlassCard hover delay={delay} className="p-5">
      <div className="flex items-start justify-between gap-3">
        <div>
          <p className="text-xs font-medium uppercase tracking-wider text-slate-400">
            {label}
          </p>
          <p className="mt-2 text-2xl font-bold tracking-tight text-white sm:text-3xl">
            {value}
          </p>
          {sub && <p className="mt-1 text-xs text-slate-500">{sub}</p>}
        </div>
        <div
          className={`flex h-11 w-11 shrink-0 items-center justify-center rounded-xl bg-gradient-to-br ${accent} border border-accent-400/15`}
        >
          <Icon className="h-5 w-5 text-accent-400" />
        </div>
      </div>
    </GlassCard>
  )
}

interface ButtonProps {
  children: ReactNode
  variant?: 'primary' | 'secondary' | 'ghost' | 'danger'
  size?: 'sm' | 'md' | 'lg'
  className?: string
  disabled?: boolean
  type?: 'button' | 'submit'
  onClick?: () => void
  icon?: LucideIcon
}

export function Button({
  children,
  variant = 'primary',
  size = 'md',
  className = '',
  disabled,
  type = 'button',
  onClick,
  icon: Icon,
}: ButtonProps) {
  const sizes = {
    sm: 'px-3 py-1.5 text-xs gap-1.5',
    md: 'px-4 py-2.5 text-sm gap-2',
    lg: 'px-6 py-3 text-sm gap-2.5',
  }

  const variants = {
    primary:
      'bg-gradient-to-r from-accent-600 to-accent-500 text-white shadow-lg shadow-accent-500/25 hover:shadow-accent-500/40 hover:brightness-110 border border-accent-400/30',
    secondary:
      'glass text-slate-200 hover:border-accent-400/30 hover:text-white',
    ghost: 'bg-transparent text-slate-400 hover:text-white hover:bg-white/5',
    danger:
      'bg-error/15 text-red-300 border border-error/30 hover:bg-error/25',
  }

  return (
    <motion.button
      type={type}
      disabled={disabled}
      onClick={onClick}
      whileHover={disabled ? undefined : { scale: 1.02 }}
      whileTap={disabled ? undefined : { scale: 0.98 }}
      className={`inline-flex items-center justify-center rounded-xl font-semibold transition-all duration-200 disabled:cursor-not-allowed disabled:opacity-40 ${sizes[size]} ${variants[variant]} ${className}`}
    >
      {Icon && <Icon className="h-4 w-4" />}
      {children}
    </motion.button>
  )
}
