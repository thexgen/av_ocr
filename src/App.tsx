import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom'
import { AppLayout } from './components/layout/AppLayout'
import { Dashboard } from './pages/Dashboard'
import { UploadPage } from './pages/Upload'
import { ProcessingPage } from './pages/Processing'
import { ReviewPage } from './pages/Review'
import { SuccessPage } from './pages/Success'

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route element={<AppLayout />}>
          <Route index element={<Dashboard />} />
          <Route path="upload" element={<UploadPage />} />
          <Route path="processing" element={<ProcessingPage />} />
          <Route path="review" element={<ReviewPage />} />
          <Route path="success" element={<SuccessPage />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Route>
      </Routes>
    </BrowserRouter>
  )
}
