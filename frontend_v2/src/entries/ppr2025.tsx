import React from 'react'
import ReactDOM from 'react-dom/client'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { BrowserRouter, Routes, Route } from 'react-router-dom'
import { Ppr2025Page } from '@features/knowledge/Ppr2025Page'

const qc = new QueryClient({ defaultOptions: { queries: { retry: 1, staleTime: 300_000 } } })

ReactDOM.createRoot(document.getElementById('root')!).render(
  <QueryClientProvider client={qc}>
    <BrowserRouter>
      <Routes><Route path="*" element={<Ppr2025Page />} /></Routes>
    </BrowserRouter>
  </QueryClientProvider>
)
