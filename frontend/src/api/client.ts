/** Thin client for the local FastAPI holding engine (proxied via /api). */

const API_BASE = '/api'

export interface UploadResponse {
  job_id: string
  status: string
}

export interface ValidationSummary {
  job_id: string
  status: string
  processing_time: string
  total_rows: number
  valid_rows: number
  error_rows: number
  warnings: string[]
  error_code?: string | null
  error_message?: string | null
  stages?: Array<{ stage: string; detail: string; at: string }>
}

export interface JobStatusResponse {
  job_id: string
  status: string
  validation_summary: ValidationSummary | null
  csv_path: string | null
  json_path: string | null
  processing_duration_ms: number | null
  processing_duration: string | null
  original_file_name?: string
  error_code?: string | null
  error_message?: string | null
}

export function isTerminalStatus(status: string): boolean {
  return (
    status === 'FAILED' ||
    status === 'SUCCESS' ||
    status === 'SUCCESS_WITH_WARNINGS'
  )
}

export function uploadHoldingFile(
  file: File,
  onProgress?: (pct: number) => void,
): Promise<UploadResponse> {
  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest()
    const form = new FormData()
    form.append('file', file)

    xhr.open('POST', `${API_BASE}/upload`)
    xhr.responseType = 'json'

    xhr.upload.onprogress = (event) => {
      if (!event.lengthComputable || !onProgress) return
      onProgress(Math.round((event.loaded / event.total) * 100))
    }

    xhr.onload = () => {
      if (xhr.status >= 200 && xhr.status < 300) {
        resolve(xhr.response as UploadResponse)
        return
      }
      const detail =
        (xhr.response && (xhr.response.detail as string)) ||
        xhr.statusText ||
        'Upload failed'
      reject(new Error(typeof detail === 'string' ? detail : JSON.stringify(detail)))
    }

    xhr.onerror = () => reject(new Error('Network error during upload'))
    xhr.send(form)
  })
}

export async function getJobStatus(jobId: string): Promise<JobStatusResponse> {
  const res = await fetch(`${API_BASE}/job/${encodeURIComponent(jobId)}`)
  if (!res.ok) {
    const body = await res.json().catch(() => ({}))
    throw new Error(
      (body as { detail?: string }).detail || `Job lookup failed (${res.status})`,
    )
  }
  return res.json() as Promise<JobStatusResponse>
}

export interface ReviewTransaction {
  id: string
  rowno?: number
  job_id?: string
  entity_id?: number
  entity_name?: string
  user_id?: number
  tradeDate: string
  type: string
  security: string
  quantity: number | null
  price: number | null
  amount: number
  status: 'valid' | 'needs_review' | 'missing_data'
  confidence: number
  originalText: string
  normalizedJson: Record<string, unknown>
  validationErrors: string[]
  aiReasoning: string
  iserror?: boolean
  errordesc?: string | null
  filename?: string
  checkno?: string | null
}

export interface JobTransactionsResponse {
  job_id: string
  status: string
  original_file_name?: string
  entity_id: number
  entity_name: string
  user_id: number
  total: number
  valid: number
  errors: number
  transactions: ReviewTransaction[]
}

export async function getJobTransactions(
  jobId: string,
): Promise<JobTransactionsResponse> {
  const res = await fetch(
    `${API_BASE}/job/${encodeURIComponent(jobId)}/transactions`,
  )
  if (!res.ok) {
    const body = await res.json().catch(() => ({}))
    throw new Error(
      (body as { detail?: string }).detail ||
        `Failed to load transactions (${res.status})`,
    )
  }
  return res.json() as Promise<JobTransactionsResponse>
}

export interface TempRowsActionResponse {
  job_id: string
  deleted?: number
  requested?: number
  processed?: number
  skipped_errors?: number
  deleted_from_temp?: number
}

async function postTempRowIds(
  jobId: string,
  action: 'delete' | 'process',
  ids: string[],
): Promise<TempRowsActionResponse> {
  const res = await fetch(
    `${API_BASE}/job/${encodeURIComponent(jobId)}/transactions/${action}`,
    {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ ids }),
    },
  )
  if (!res.ok) {
    const body = await res.json().catch(() => ({}))
    throw new Error(
      (body as { detail?: string }).detail ||
        `Failed to ${action} transactions (${res.status})`,
    )
  }
  return res.json() as Promise<TempRowsActionResponse>
}

export function deleteJobTransactions(jobId: string, ids: string[]) {
  return postTempRowIds(jobId, 'delete', ids)
}

export function processJobTransactions(jobId: string, ids: string[]) {
  return postTempRowIds(jobId, 'process', ids)
}

export function downloadCsvUrl(jobId: string): string {
  return `${API_BASE}/job/${encodeURIComponent(jobId)}/download/csv`
}

export function downloadJsonUrl(jobId: string): string {
  return `${API_BASE}/job/${encodeURIComponent(jobId)}/download/json`
}

export const JOB_STORAGE_KEY = 'holdingJob'

export interface VehicleProgressStep {
  key: string
  label: string
  status: string
  detail?: string | null
}

export interface VehicleUploadResponse {
  status: string
  job_id?: string | null
  vehicle_type?: string | null
  file_name?: string
  rows_staged?: number
  clean_rows?: number
  error_rows?: number
  steps?: VehicleProgressStep[]
  message?: string
  warning?: string
  redirect_to?: string | null
}

export async function uploadVehicleFile(
  file: File,
  vehicle: string,
): Promise<VehicleUploadResponse> {
  const form = new FormData()
  form.append('file', file)
  form.append('vehicle', vehicle)
  const res = await fetch(`${API_BASE}/vehicle/upload`, {
    method: 'POST',
    body: form,
  })
  if (!res.ok) {
    const body = await res.json().catch(() => ({}))
    throw new Error(
      (body as { detail?: string }).detail || `Vehicle upload failed (${res.status})`,
    )
  }
  return res.json() as Promise<VehicleUploadResponse>
}

export interface VehicleStagingRow {
  id: string
  jobId?: string | null
  entityId: string
  entityName: string
  folioOrIsin: string
  tradeDate: string
  type: string
  schemeOrInstrument: string
  units: number
  navOrPrice: number
  amount: number
  iserror?: boolean
  errordesc?: string | null
  filename?: string | null
}

export async function fetchVehicleStaging(
  vehicle: string,
  options?: {
    jobId?: string
    limit?: number
  },
): Promise<VehicleStagingRow[]> {
  const params = new URLSearchParams()
  if (options?.jobId) params.set('job_id', options.jobId)
  if (options?.limit) params.set('limit', String(options.limit))
  const qs = params.toString()
  const res = await fetch(
    `${API_BASE}/vehicle/${encodeURIComponent(vehicle)}/staging${qs ? `?${qs}` : ''}`,
  )
  if (!res.ok) {
    const body = await res.json().catch(() => ({}))
    throw new Error(
      (body as { detail?: string }).detail ||
        `Failed to load ${vehicle} staging (${res.status})`,
    )
  }
  const data = (await res.json()) as { transactions?: VehicleStagingRow[] }
  return data.transactions ?? []
}

/** @deprecated use fetchVehicleStaging('mutual-fund', …) */
export function fetchMutualFundStaging(options?: {
  jobId?: string
  limit?: number
}): Promise<VehicleStagingRow[]> {
  return fetchVehicleStaging('mutual-fund', options)
}

export interface LedgerFilterOptions {
  entityId?: string | number
  accountId?: string | number
  fromDate?: string
  toDate?: string
  limit?: number
}

export interface BankCashLedgerRow {
  id: string
  entityId: string
  entityName: string
  accountId: string
  accountLabel: string
  tradeDate: string
  type: string
  description: string
  checkNo: string
  amount: number
  balance: number
}

function appendLedgerParams(
  params: URLSearchParams,
  options?: LedgerFilterOptions,
) {
  if (options?.entityId != null && options.entityId !== '' && options.entityId !== 'all') {
    params.set('entity_id', String(options.entityId))
  }
  if (
    options?.accountId != null &&
    options.accountId !== '' &&
    options.accountId !== 'all'
  ) {
    params.set('account_id', String(options.accountId))
  }
  if (options?.fromDate) params.set('from_date', options.fromDate)
  if (options?.toDate) params.set('to_date', options.toDate)
  if (options?.limit) params.set('limit', String(options.limit))
}

export async function fetchBankCashLedger(
  options?: LedgerFilterOptions,
): Promise<BankCashLedgerRow[]> {
  const params = new URLSearchParams()
  appendLedgerParams(params, options)
  const qs = params.toString()
  const res = await fetch(`${API_BASE}/bankcash/ledger${qs ? `?${qs}` : ''}`)
  if (!res.ok) {
    const body = await res.json().catch(() => ({}))
    throw new Error(
      (body as { detail?: string }).detail ||
        `Failed to load bank cash ledger (${res.status})`,
    )
  }
  const data = (await res.json()) as { transactions?: BankCashLedgerRow[] }
  return data.transactions ?? []
}

export async function fetchVehicleLedger(
  vehicle: string,
  options?: LedgerFilterOptions,
): Promise<VehicleStagingRow[]> {
  const params = new URLSearchParams()
  appendLedgerParams(params, options)
  const qs = params.toString()
  const res = await fetch(
    `${API_BASE}/vehicle/${encodeURIComponent(vehicle)}/ledger${qs ? `?${qs}` : ''}`,
  )
  if (!res.ok) {
    const body = await res.json().catch(() => ({}))
    throw new Error(
      (body as { detail?: string }).detail ||
        `Failed to load ${vehicle} ledger (${res.status})`,
    )
  }
  const data = (await res.json()) as { transactions?: VehicleStagingRow[] }
  return data.transactions ?? []
}

async function postVehicleTempRowIds(
  vehicle: string,
  action: 'delete' | 'process',
  jobId: string,
  ids: string[],
): Promise<TempRowsActionResponse> {
  const res = await fetch(
    `${API_BASE}/vehicle/${encodeURIComponent(vehicle)}/staging/${action}`,
    {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ job_id: jobId, ids }),
    },
  )
  if (!res.ok) {
    const body = await res.json().catch(() => ({}))
    throw new Error(
      (body as { detail?: string }).detail ||
        `Failed to ${action} ${vehicle} rows (${res.status})`,
    )
  }
  return res.json() as Promise<TempRowsActionResponse>
}

export function deleteVehicleStaging(
  vehicle: string,
  jobId: string,
  ids: string[],
) {
  return postVehicleTempRowIds(vehicle, 'delete', jobId, ids)
}

export function processVehicleStaging(
  vehicle: string,
  jobId: string,
  ids: string[],
) {
  return postVehicleTempRowIds(vehicle, 'process', jobId, ids)
}
