import type { ReactNode } from 'react'
import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom'
import { AppLayout } from './components/layout/AppLayout'
import { Dashboard } from './pages/Dashboard'
import { BankCashPage } from './pages/BankCash'
import { SuccessPage } from './pages/Success'
import { KnowledgeRepositoryPage } from './pages/KnowledgeRepository'
import { isAdmin } from './config/flags'

function AdminOnly({ children }: { children: ReactNode }) {
  if (!isAdmin()) return <Navigate to="/" replace />
  return <>{children}</>
}

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route element={<AppLayout />}>
          <Route index element={<Dashboard />} />
          <Route path="transactions/bank-cash" element={<BankCashPage />} />
          <Route
            path="settings/knowledge-repository"
            element={
              <AdminOnly>
                <KnowledgeRepositoryPage />
              </AdminOnly>
            }
          />
          <Route
            path="upload"
            element={<Navigate to="/transactions/bank-cash?tab=upload" replace />}
          />
          <Route
            path="processing"
            element={<Navigate to="/transactions/bank-cash?tab=upload" replace />}
          />
          <Route
            path="review"
            element={<Navigate to="/transactions/bank-cash?tab=upload" replace />}
          />
          <Route path="success" element={<SuccessPage />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Route>
      </Routes>
    </BrowserRouter>
  )
}
