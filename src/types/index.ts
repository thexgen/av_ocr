export type TransactionStatus = 'valid' | 'needs_review' | 'missing_data'

export type TransactionType =
  | 'Buy'
  | 'Sell'
  | 'Dividend'
  | 'Interest'
  | 'Deposit'
  | 'Withdrawal'
  | 'Transfer'
  | 'Fee'

export interface Transaction {
  id: string
  tradeDate: string
  type: TransactionType
  security: string
  quantity: number | null
  price: number | null
  amount: number
  status: TransactionStatus
  confidence: number
  originalText: string
  normalizedJson: Record<string, unknown>
  validationErrors: string[]
  aiReasoning: string
}

export interface RecentImport {
  id: string
  fileName: string
  uploadedAt: string
  status: 'completed' | 'processing' | 'failed' | 'review'
  transactionCount: number
  broker: string
}

export interface ImportStats {
  totalImports: number
  transactionsExtracted: number
  avgConfidence: number
  pendingReview: number
}

export interface UploadFile {
  id: string
  file: File
  size: number
  status: 'queued' | 'ready' | 'error'
  error?: string
}

export interface ProcessingStep {
  id: string
  label: string
  description: string
}

export interface SuccessSummary {
  processed: number
  skipped: number
  warnings: number
  fileName: string
  importId: string
  completedAt: string
}
