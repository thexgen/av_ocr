export async function uploadDocument(file: File) {
  const form = new FormData()
  form.append('file', file)

  const resp = await fetch('/api/documents/upload', {
    method: 'POST',
    body: form,
  })

  const bodyText = await resp.text()
  let body: Record<string, unknown> | null = null

  if (bodyText) {
    try {
      body = JSON.parse(bodyText) as Record<string, unknown>
    } catch {
      body = { detail: bodyText }
    }
  }

  if (!resp.ok) {
    const detail = body?.detail
    const msg =
      typeof detail === 'string'
        ? detail
        : resp.statusText || 'Upload failed'
    throw new Error(msg)
  }

  return body
}
