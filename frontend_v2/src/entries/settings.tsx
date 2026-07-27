import React from 'react'
import ReactDOM from 'react-dom/client'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { BrowserRouter, Routes, Route } from 'react-router-dom'
import { SettingsPage } from '@features/settings/SettingsPage'

const qc = new QueryClient({ defaultOptions: { queries: { retry: 1, staleTime: 300_000 } } })

ReactDOM.createRoot(document.getElementById('root')!).render(
  <QueryClientProvider client={qc}>
    <BrowserRouter>
      <Routes><Route path="*" element={<SettingsPage />} /></Routes>
    </BrowserRouter>
  </QueryClientProvider>
)
