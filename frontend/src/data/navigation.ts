import type { LucideIcon } from 'lucide-react'
import {
  Home,
  ArrowLeftRight,
  Landmark,
  PieChart,
  Coins,
  TrendingUp,
  Building2,
  RefreshCw,
  LayoutDashboard,
  Briefcase,
  BarChart3,
  BookOpen,
  LineChart,
  Scale,
  FileSpreadsheet,
  ScrollText,
  Settings,
  Library,
} from 'lucide-react'
import { isAdmin } from '../config/flags'

export type NavLeaf = {
  id: string
  label: string
  path?: string
  icon: LucideIcon
  soon?: boolean
  adminOnly?: boolean
}

export type NavGroup = {
  id: string
  label: string
  icon: LucideIcon
  children: NavLeaf[]
  adminOnly?: boolean
}

export type NavItem = NavLeaf | NavGroup

export function isNavGroup(item: NavItem): item is NavGroup {
  return 'children' in item
}

export const navigation: NavItem[] = [
  {
    id: 'home',
    label: 'Home',
    path: '/',
    icon: Home,
  },
  {
    id: 'transactions',
    label: 'Transactions',
    icon: ArrowLeftRight,
    children: [
      { id: 'bank-cash', label: 'Bank Cash', path: '/transactions/bank-cash', icon: Landmark },
      {
        id: 'mutual-fund',
        label: 'Mutual Fund',
        path: '/transactions/mutual-fund',
        icon: PieChart,
      },
      {
        id: 'fixed-income',
        label: 'Fixed Income',
        path: '/transactions/fixed-income',
        icon: Coins,
      },
      {
        id: 'direct-equity',
        label: 'Direct Equity',
        path: '/transactions/direct-equity',
        icon: TrendingUp,
      },
      { id: 'real-estate', label: 'Real Estate', icon: Building2, soon: true },
      { id: 'txn-sync', label: 'Transaction Sync', icon: RefreshCw, soon: true },
    ],
  },
  {
    id: 'dashboard',
    label: 'Dashboard',
    icon: LayoutDashboard,
    children: [
      { id: 'portfolio-1', label: 'Portfolio 1', icon: Briefcase, soon: true },
      { id: 'portfolio-2', label: 'Portfolio 2', icon: Briefcase, soon: true },
    ],
  },
  {
    id: 'analytics',
    label: 'Analytics',
    icon: BarChart3,
    children: [
      { id: 'wealth-register', label: 'Wealth Register', icon: BookOpen, soon: true },
      { id: 'portfolio-perf', label: 'Portfolio Performance', icon: LineChart, soon: true },
    ],
  },
  {
    id: 'general-ledger',
    label: 'General Ledger',
    icon: Scale,
    children: [
      { id: 'balance-sheet', label: 'Balance Sheet', icon: FileSpreadsheet, soon: true },
      { id: 'gains-report', label: 'Gains Report', icon: TrendingUp, soon: true },
      { id: 'income-statement', label: 'Income Statement', icon: ScrollText, soon: true },
    ],
  },
  {
    id: 'settings',
    label: 'Settings',
    icon: Settings,
    adminOnly: true,
    children: [
      {
        id: 'knowledge-repository',
        label: 'Knowledge Repository',
        path: '/settings/knowledge-repository',
        icon: Library,
        adminOnly: true,
      },
    ],
  },
]

/** Nav filtered by admin flag (real auth later). */
export function getVisibleNavigation(): NavItem[] {
  const admin = isAdmin()
  return navigation
    .filter((item) => !item.adminOnly || admin)
    .map((item) => {
      if (!isNavGroup(item)) return item
      return {
        ...item,
        children: item.children.filter((child) => !child.adminOnly || admin),
      }
    })
    .filter((item) => !isNavGroup(item) || item.children.length > 0)
}
