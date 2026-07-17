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

export function downloadCsvUrl(jobId: string): string {
  return `${API_BASE}/job/${encodeURIComponent(jobId)}/download/csv`
}

export function downloadJsonUrl(jobId: string): string {
  return `${API_BASE}/job/${encodeURIComponent(jobId)}/download/json`
}

export const JOB_STORAGE_KEY = 'holdingJob'
