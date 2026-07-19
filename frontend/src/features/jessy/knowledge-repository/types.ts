export type DocumentStatus = 'Ready' | 'Processing' | 'Failed'

export interface KnowledgeDocument {
  id: string
  name: string
  uploadDate: string
  status: DocumentStatus
}
