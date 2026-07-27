import { useState } from 'react'

export interface EvidenceRecord {
  id: string
  label: string
  source: string
  status: 'verified' | 'warning' | 'failed'
  detail: string
}

export function useWidgetEvidence(_widgetId: string) {
  const [evidenceOpen, setEvidenceOpen] = useState(false)
  const [drawerOpen, setDrawerOpen] = useState(false)

  const toggleEvidence = () => setEvidenceOpen((v) => !v)
  const toggleDrawer = () => setDrawerOpen((v) => !v)

  return {
    evidenceOpen,
    drawerOpen,
    toggleEvidence,
    toggleDrawer,
    setEvidenceOpen,
    setDrawerOpen,
  }
}
