import { useMemo, useState } from 'react'
import { uploadDocument } from './service'
import type { KnowledgeDocument } from './types'

export function useKnowledgeRepository() {
  const [documents, setDocuments] = useState<KnowledgeDocument[]>([])
  const [uploading, setUploading] = useState(false)
  const [notification, setNotification] = useState<string | null>(null)

  const stats = useMemo(
    () => ({
      total: documents.length,
      ready: documents.filter((d) => d.status === 'Ready').length,
      processing: documents.filter((d) => d.status === 'Processing').length,
      failed: documents.filter((d) => d.status === 'Failed').length,
    }),
    [documents],
  )

  const addDocuments = async (files: FileList | null) => {
    if (uploading || !files || files.length === 0) return

    setUploading(true)
    setNotification(null)

    try {
      for (let i = 0; i < files.length; i++) {
        const file = files[i]
        if (!file.name.toLowerCase().endsWith('.pdf')) continue

        const tempId = `${Date.now()}-${i}`
        setDocuments((previous) => [
          {
            id: tempId,
            name: file.name,
            uploadDate: new Date().toLocaleDateString('en-US', {
              month: 'short',
              day: 'numeric',
              year: 'numeric',
            }),
            status: 'Processing',
          },
          ...previous,
        ])

        try {
          await uploadDocument(file)
          setDocuments((previous) =>
            previous.map((doc) =>
              doc.id === tempId ? { ...doc, status: 'Ready' } : doc,
            ),
          )
          setNotification(`Uploaded ${file.name} successfully.`)
        } catch (err) {
          setDocuments((previous) =>
            previous.map((doc) =>
              doc.id === tempId ? { ...doc, status: 'Failed' } : doc,
            ),
          )
          const msg = err instanceof Error ? err.message : 'Upload failed'
          setNotification(msg)
        }
      }
    } finally {
      setUploading(false)
    }
  }

  const deleteDocument = (documentId: string) => {
    setDocuments((previous) => previous.filter((doc) => doc.id !== documentId))
  }

  return {
    documents,
    stats,
    addDocuments,
    deleteDocument,
    uploading,
    notification,
  }
}
