import React from 'react'
import ReactDOM from 'react-dom/client'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { BrowserRouter, Routes, Route } from 'react-router-dom'
import { ScreenTemplate } from '@layouts/index'
import { ClauseExplorer } from '@features/knowledge/ClauseExplorer'

const qc = new QueryClient({ defaultOptions: { queries: { retry: 1, staleTime: 300_000 } } })

function ClausesPage() {
  return (
    <ScreenTemplate
      header={<><h1>Clause Explorer</h1><p>Browse, search and analyze PPR clauses</p></>}
      primary={<ClauseExplorer />}
    />
  )
}

ReactDOM.createRoot(document.getElementById('root')!).render(
  <QueryClientProvider client={qc}>
    <BrowserRouter>
      <Routes><Route path="*" element={<ClausesPage />} /></Routes>
    </BrowserRouter>
  </QueryClientProvider>
)
