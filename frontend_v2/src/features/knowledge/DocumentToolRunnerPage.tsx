import { useMemo, useState, type FormEvent } from 'react'
import { ArrowLeft, Download } from 'lucide-react'
import { useNavigate, useParams } from 'react-router-dom'
import { ScreenTemplate } from '@layouts/index'
import { Card } from '@shared/ui/Card'
import { Button } from '@shared/ui/Button'
import { Input } from '@shared/ui/Input'
import { fetchJson } from '@entities/sharedApi'
import { authReady } from '@entities/bootstrapAuth'
import { getAuthToken } from '@entities/authToken'

type FormState = Record<string, string>

const CONFIG: Record<string, { title: string; description: string }> = {
  resume: { title: 'Resume Generator', description: 'Generate a contractor profile from live company intelligence.' },
  'vat-tax': { title: 'VAT/Tax Calculator', description: 'Run the VAT and tax agent against a tender price.' },
  'boq-estimator': { title: 'BOQ Estimator', description: 'Estimate a BOQ item from PostgreSQL SOR rates.' },
  export: { title: 'Document Export', description: 'Download the complete tender analysis bundle.' },
  'bulk-upload': { title: 'Bulk Upload', description: 'Upload tender notice, TDS, BOQ and SOR documents for processing.' },
  'sor-lookup': { title: 'SOR Lookup', description: 'Search and compare live BWDB, PWD and LGED SOR rates.' },
}

const INITIAL: Record<string, FormState> = {
  resume: { contractor_id: '' },
  'vat-tax': { contract_value: '10000000', vat_rate: '7.5', ait_rate: '5', sd_rate: '0', company_tax_rate: '27.5' },
  'boq-estimator': { code: '40-200-00', description: '', agency: 'BWDB', zone: 'A', unit: '', quantity: '1' },
  export: { tender_id: '' },
  'bulk-upload': { tender_id: '', agency: 'BWDB', zone: 'A' },
  'sor-lookup': { code: '40-200-00', description: '', agency: 'BWDB', zone: 'A' },
}

async function downloadAuthenticated(url: string, filename: string) {
  await authReady()
  const response = await fetch(url, { headers: { Authorization: `Bearer ${getAuthToken() ?? ''}` } })
  if (!response.ok) throw new Error(`Download failed (HTTP ${response.status})`)
  const href = URL.createObjectURL(await response.blob())
  const link = document.createElement('a')
  link.href = href
  link.download = filename
  link.click()
  URL.revokeObjectURL(href)
}

function JsonResult({ value }: { value: unknown }) {
  if (!value) return null
  return (
    <Card className="p-4">
      <h2 className="mb-2 text-sm font-semibold text-gray-900 dark:text-white">Live result</h2>
      <pre className="max-h-[32rem] overflow-auto whitespace-pre-wrap rounded-lg bg-gray-950 p-4 text-xs text-emerald-300">
        {JSON.stringify(value, null, 2)}
      </pre>
    </Card>
  )
}

export function DocumentToolRunnerPage() {
  const { tool = '' } = useParams()
  const navigate = useNavigate()
  const config = CONFIG[tool]
  const [form, setForm] = useState<FormState>(() => INITIAL[tool] ?? {})
  const [files, setFiles] = useState<Record<string, File | undefined>>({})
  const [result, setResult] = useState<unknown>()
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)
  const set = (key: string, value: string) => setForm(current => ({ ...current, [key]: value }))

  const fields = useMemo(() => {
    if (tool === 'resume') return [['contractor_id', 'Contractor ID']]
    if (tool === 'vat-tax') return [['contract_value', 'Contract value (BDT)'], ['vat_rate', 'VAT rate (%)'], ['ait_rate', 'AIT rate (%)'], ['sd_rate', 'SD rate (%)'], ['company_tax_rate', 'Company tax rate (%)']]
    if (tool === 'export') return [['tender_id', 'Tender ID']]
    if (tool === 'bulk-upload') return [['tender_id', 'Tender ID'], ['agency', 'SOR agency'], ['zone', 'Zone']]
    return [['code', 'SOR item code'], ['description', 'Description'], ['agency', 'Agency'], ['zone', 'Zone'], ...(tool === 'boq-estimator' ? [['unit', 'Unit'], ['quantity', 'Quantity']] : [])]
  }, [tool])

  if (!config) {
    return <ScreenTemplate header={<h1 className="text-lg font-semibold">Tool not found</h1>} primary={<Button onClick={() => navigate('/knowledge/document-tools')}>Back to tools</Button>} />
  }

  async function run(event: FormEvent) {
    event.preventDefault()
    setBusy(true)
    setError('')
    setResult(undefined)
    try {
      if (tool === 'resume') {
        setResult(await fetchJson(`/api/generate/resume/${encodeURIComponent(form.contractor_id)}`, true))
      } else if (tool === 'vat-tax') {
        const input = Object.fromEntries(Object.entries(form).map(([key, value]) => [key, Number(value)]))
        setResult(await fetchJson('/api/v1/agents/agent-033-vat-tax-calculator/run', { method: 'POST', body: JSON.stringify(input) }))
      } else if (tool === 'boq-estimator') {
        setResult(await fetchJson('/api/pricing/estimate', { method: 'POST', body: JSON.stringify({
          agency: form.agency,
          zone: form.zone,
          items: [{ code: form.code, description: form.description, unit: form.unit, quantity: Number(form.quantity), agency: form.agency, zone: form.zone }],
        }) }))
      } else if (tool === 'sor-lookup') {
        const qs = new URLSearchParams(form)
        setResult(await fetchJson(`/api/sor/lookup?${qs}`, true))
      } else if (tool === 'export') {
        await downloadAuthenticated(`/api/tender/${encodeURIComponent(form.tender_id)}/bundle`, `tender-${form.tender_id}-bundle.zip`)
        setResult({ success: true, message: 'Tender bundle downloaded.', tender_id: form.tender_id })
      } else {
        const body = new FormData()
        Object.entries(files).forEach(([key, file]) => { if (file) body.append(key, file) })
        const qs = new URLSearchParams({ tender_id: form.tender_id, sor_agency: form.agency, zone: form.zone })
        setResult(await fetchJson(`/api/tender/upload?${qs}`, { method: 'POST', body }))
      }
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'Tool failed')
    } finally {
      setBusy(false)
    }
  }

  return (
    <ScreenTemplate
      header={
        <div className="flex items-start gap-3">
          <Button variant="ghost" size="sm" onClick={() => navigate('/knowledge/document-tools')} leftIcon={<ArrowLeft className="h-4 w-4" />}>Tools</Button>
          <div><h1 className="text-lg font-semibold text-gray-900 dark:text-white">{config.title}</h1><p className="text-sm text-gray-500">{config.description}</p></div>
        </div>
      }
      primary={
        <div className="space-y-4">
          <Card className="p-5">
            <form className="grid gap-4 sm:grid-cols-2" onSubmit={run}>
              {fields.map(([key, label]) => <Input key={key} label={label} value={form[key] ?? ''} required={['contractor_id', 'contract_value', 'tender_id', 'code'].includes(key)} onChange={e => set(key, e.target.value)} />)}
              {tool === 'bulk-upload' && ['notice', 'tds', 'tds_2', 'boq', 'sor'].map(key => (
                <Input key={key} type="file" label={`${key.toUpperCase()} document`} onChange={e => setFiles(current => ({ ...current, [key]: e.target.files?.[0] }))} />
              ))}
              <div className="sm:col-span-2">
                <Button type="submit" isLoading={busy} leftIcon={tool === 'export' ? <Download className="h-4 w-4" /> : undefined}>
                  {tool === 'export' ? 'Download bundle' : tool === 'bulk-upload' ? 'Upload & process' : 'Run tool'}
                </Button>
              </div>
            </form>
            {error && <p className="mt-4 rounded-lg bg-red-50 p-3 text-sm text-red-700" role="alert">{error}</p>}
          </Card>
          <JsonResult value={result} />
        </div>
      }
    />
  )
}
