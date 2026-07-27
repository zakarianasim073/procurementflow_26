import React from 'react'
import ReactDOM from 'react-dom/client'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { BrowserRouter, Routes, Route } from 'react-router-dom'
import { ScreenTemplate } from '@layouts/index'
import { PricingLaboratory } from '@features/tender/PricingLaboratory'

const qc = new QueryClient({ defaultOptions: { queries: { retry: 1, staleTime: 300_000 } } })

function PricingPage() {
  return (
    <ScreenTemplate
      header={<><h1>Pricing Laboratory</h1><p>BOQ item rate analysis and comparison</p></>}
      primary={<PricingLaboratory />}
    />
  )
}

ReactDOM.createRoot(document.getElementById('root')!).render(
  <QueryClientProvider client={qc}>
    <BrowserRouter>
      <Routes><Route path="*" element={<PricingPage />} /></Routes>
    </BrowserRouter>
  </QueryClientProvider>
)
