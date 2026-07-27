import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { BarChart3, Upload, ArrowLeft, CheckCircle, XCircle, AlertTriangle, FileText } from 'lucide-react'
import { cn } from '@shared/lib/cn'
import { Tabs, TabsList, TabsTrigger, TabsContent } from '@shared/ui/Tabs'
import { Button } from '@shared/ui/Button'
import { Input } from '@shared/ui/Input'
import { Card } from '@shared/ui/Card'
import { Badge } from '@shared/ui/Badge'
import { Skeleton } from '@shared/ui/Skeleton'
import { EmptyState } from '@shared/ui/EmptyState'
import { ScreenTemplate } from '@layouts/index'
import { useBoqResult, useBoqUpload, useBoqCompare } from '@hooks/index'
import type { BoqItem } from '@entities/boq'

function BoqSummaryCard({ item }: { item: BoqItem }) {
  const variance = item.pct_diff ?? 0
  const flag = item.flag ?? ''
  const isMatched = flag === 'match' || flag === 'exact'
  const status = isMatched ? 'matched' : Math.abs(variance) < 5 ? 'close' : 'mismatch'

  return (
    <div className={cn(
      'rounded-xl border p-4 transition-colors',
      status === 'matched' && 'border-green-200 bg-green-50 dark:border-green-800 dark:bg-green-900/20',
      status === 'close' && 'border-yellow-200 bg-yellow-50 dark:border-yellow-800 dark:bg-yellow-900/20',
      status === 'mismatch' && 'border-red-200 bg-red-50 dark:border-red-800 dark:bg-red-900/20',
    )}>
      <div className="flex items-start justify-between">
        <div>
          <div className="flex items-center gap-2">
            <span className="font-mono text-xs font-medium text-gray-600 dark:text-gray-400">{item.code}</span>
            {isMatched ? (
              <CheckCircle className="h-4 w-4 text-green-500" />
            ) : variance < 0 ? (
              <AlertTriangle className="h-4 w-4 text-yellow-500" />
            ) : (
              <XCircle className="h-4 w-4 text-red-500" />
            )}
          </div>
          <p className="mt-1 text-sm text-gray-900 dark:text-white">{item.desc}</p>
        </div>
        <Badge tone={status === 'matched' ? 'success' : status === 'close' ? 'warning' : 'danger'}>
          {status === 'matched' ? 'Matched' : status === 'close' ? 'Close' : 'Mismatch'}
        </Badge>
      </div>
      <div className="mt-3 grid grid-cols-4 gap-2 text-xs">
        <div>
          <span className="text-gray-500 dark:text-gray-400">Qty</span>
          <p className="font-medium text-gray-900 dark:text-white">{item.qty} {item.unit}</p>
        </div>
        <div>
          <span className="text-gray-500 dark:text-gray-400">BOQ Rate</span>
          <p className="font-medium text-gray-900 dark:text-white">৳{item.rate?.toLocaleString()}</p>
        </div>
        <div>
          <span className="text-gray-500 dark:text-gray-400">SOR Rate</span>
          <p className="font-medium text-gray-900 dark:text-white">{item.sor_rate ? `৳${item.sor_rate.toLocaleString()}` : '—'}</p>
        </div>
        <div>
          <span className="text-gray-500 dark:text-gray-400">Variance</span>
          <p className={cn(
            'font-medium',
            variance === 0 ? 'text-green-600 dark:text-green-400' : variance < 0 ? 'text-yellow-600 dark:text-yellow-400' : 'text-red-600 dark:text-red-400'
          )}>
            {variance > 0 ? '+' : ''}{variance.toFixed(1)}%
          </p>
        </div>
      </div>
    </div>
  )
}

export function BoqPage() {
  const navigate = useNavigate()
  const [tenderId, setTenderId] = useState('')
  const [sorAgency, setSorAgency] = useState('BWDB')
  const [zone, setZone] = useState('A')
  const [activeTab, setActiveTab] = useState<'summary' | 'items' | 'upload'>('summary')

  const { data: boqResult, isLoading } = useBoqResult(tenderId)
  const uploadMutation = useBoqUpload()
  const compareMutation = useBoqCompare()

  const handleUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (file && tenderId) {
      uploadMutation.mutate({ file })
    }
  }

  const handleCompare = () => {
    if (tenderId) {
      compareMutation.mutate({ boqFileId: tenderId, sorAgency, zone })
    }
  }

  const summary = boqResult?.summary

  return (
    <ScreenTemplate
      header={
        <div className="flex items-center gap-3">
          <button onClick={() => navigate('/tender')} className="rounded-lg p-1.5 text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-800">
            <ArrowLeft size={18} />
          </button>
          <div>
            <h1 className="text-lg font-semibold text-gray-900 dark:text-white">BOQ Analysis</h1>
            <p className="text-sm text-gray-500 dark:text-gray-400">Upload, compare, and analyze Bill of Quantities</p>
          </div>
        </div>
      }
      primary={
        <div className="space-y-6">
          {/* Tender Selection */}
          <Card className="p-4">
            <div className="flex flex-wrap items-end gap-4">
              <Input
                label="Tender ID"
                value={tenderId}
                onChange={(e) => setTenderId(e.target.value)}
                placeholder="e.g. 1298004"
                className="w-48"
              />
              <div className="flex flex-wrap items-end gap-2">
                <div>
                  <span className="mb-1 block text-xs font-medium text-gray-600 dark:text-gray-400">SOR agency</span>
                  <div className="inline-flex rounded-lg border border-gray-300 bg-white p-1 dark:border-gray-600 dark:bg-gray-800" role="radiogroup" aria-label="SOR agency">
                    {['BWDB', 'LGED', 'PWD'].map((agency) => (
                      <button
                        key={agency}
                        type="button"
                        role="radio"
                        aria-checked={sorAgency === agency}
                        onClick={() => setSorAgency(agency)}
                        className={cn(
                          'rounded-md px-3 py-1.5 text-sm font-medium transition-colors',
                          sorAgency === agency
                            ? 'bg-blue-600 text-white shadow-sm'
                            : 'text-gray-600 hover:bg-gray-100 dark:text-gray-300 dark:hover:bg-gray-700',
                        )}
                      >
                        {agency}
                      </button>
                    ))}
                  </div>
                </div>
                <label className="text-xs font-medium text-gray-600 dark:text-gray-400">
                  Zone
                <select
                  value={zone}
                  onChange={(e) => setZone(e.target.value)}
                  className="mt-1 block rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm font-normal dark:border-gray-600 dark:bg-gray-800"
                >
                  <option value="A">Zone A</option>
                  <option value="B">Zone B</option>
                  <option value="C">Zone C</option>
                  <option value="D">Zone D</option>
                </select>
                </label>
              </div>
              <Button onClick={handleCompare} disabled={!tenderId || compareMutation.isPending}>
                {compareMutation.isPending ? 'Comparing...' : 'Run Comparison'}
              </Button>
            </div>
          </Card>

          {/* Summary KPIs */}
          {summary && (
            <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
              <Card className="p-4">
                <p className="text-xs text-gray-500 dark:text-gray-400">Total Items</p>
                <p className="text-2xl font-bold text-gray-900 dark:text-white">{summary.total_items}</p>
              </Card>
              <Card className="p-4">
                <p className="text-xs text-gray-500 dark:text-gray-400">Matched</p>
                <p className="text-2xl font-bold text-green-600 dark:text-green-400">{summary.matched_items}</p>
              </Card>
              <Card className="p-4">
                <p className="text-xs text-gray-500 dark:text-gray-400">Variances</p>
                <p className="text-2xl font-bold text-yellow-600 dark:text-yellow-400">{summary.variance_items}</p>
              </Card>
              <Card className="p-4">
                <p className="text-xs text-gray-500 dark:text-gray-400">Mismatched</p>
                <p className="text-2xl font-bold text-red-600 dark:text-red-400">{summary.mismatched_items}</p>
              </Card>
            </div>
          )}

          {/* Tabs */}
          <Tabs value={activeTab} onValueChange={(v) => setActiveTab(v as typeof activeTab)}>
            <TabsList>
              <TabsTrigger value="summary">
                <BarChart3 className="h-4 w-4 mr-2" />
                Summary
              </TabsTrigger>
              <TabsTrigger value="items">
                <FileText className="h-4 w-4 mr-2" />
                Items
              </TabsTrigger>
              <TabsTrigger value="upload">
                <Upload className="h-4 w-4 mr-2" />
                Upload
              </TabsTrigger>
            </TabsList>

            <TabsContent value="summary">
              {isLoading ? (
                <div className="space-y-3">
                  {Array.from({ length: 4 }).map((_, i) => <Skeleton key={i} className="h-24 w-full rounded-xl" />)}
                </div>
              ) : !boqResult ? (
                <EmptyState
                  title="No BOQ data"
                  description="Upload a BOQ file or run comparison to see results."
                />
              ) : (
                <div className="space-y-3">
{boqResult.items.slice(0, 10).map((item) => (
                      <BoqSummaryCard key={item.code} item={item} />
                    ))}
                </div>
              )}
            </TabsContent>

            <TabsContent value="items">
              {!boqResult ? (
                <EmptyState title="No items" description="Run BOQ comparison to view items." />
              ) : (
                <div className="overflow-x-auto">
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="border-b border-gray-200 dark:border-gray-700">
                        <th className="px-4 py-3 text-left font-medium text-gray-500 dark:text-gray-400">Code</th>
                        <th className="px-4 py-3 text-left font-medium text-gray-500 dark:text-gray-400">Description</th>
                        <th className="px-4 py-3 text-right font-medium text-gray-500 dark:text-gray-400">Qty</th>
                        <th className="px-4 py-3 text-right font-medium text-gray-500 dark:text-gray-400">BOQ Rate</th>
                        <th className="px-4 py-3 text-right font-medium text-gray-500 dark:text-gray-400">SOR Rate</th>
                        <th className="px-4 py-3 text-right font-medium text-gray-500 dark:text-gray-400">Variance</th>
                      </tr>
                    </thead>
                    <tbody>
                      {boqResult.items.map((item) => (
                        <tr key={item.code} className="border-b border-gray-100 dark:border-gray-800">
                          <td className="px-4 py-3 font-mono text-xs text-gray-600 dark:text-gray-400">{item.code}</td>
                          <td className="px-4 py-3 text-gray-900 dark:text-white">{item.desc}</td>
                          <td className="px-4 py-3 text-right tabular-nums text-gray-900 dark:text-white">{item.qty}</td>
                          <td className="px-4 py-3 text-right tabular-nums text-gray-900 dark:text-white">৳{item.rate?.toLocaleString()}</td>
                          <td className="px-4 py-3 text-right tabular-nums text-gray-900 dark:text-white">
                            {item.sor_rate ? `৳${item.sor_rate.toLocaleString()}` : '—'}
                          </td>
                          <td className={cn(
                            'px-4 py-3 text-right tabular-nums font-medium',
                            (item.pct_diff ?? 0) === 0 ? 'text-green-600 dark:text-green-400' : 'text-yellow-600 dark:text-yellow-400'
                          )}>
                            {item.pct_diff != null ? `${item.pct_diff > 0 ? '+' : ''}${item.pct_diff.toFixed(1)}%` : '—'}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </TabsContent>

            <TabsContent value="upload">
              <Card className="p-6">
                <div className="flex flex-col items-center gap-4">
                  <Upload className="h-12 w-12 text-gray-400" />
                  <div className="text-center">
                    <p className="text-sm font-medium text-gray-900 dark:text-white">Upload BOQ PDF</p>
                    <p className="text-xs text-gray-500 dark:text-gray-400">Supports BWDB, PWD, LGED BOQ formats</p>
                  </div>
                  <label>
                    <input type="file" accept=".pdf" className="hidden" onChange={handleUpload} />
                    <Button variant="primary">
                      Choose File
                    </Button>
                  </label>
                  {uploadMutation.isPending && <p className="text-sm text-gray-500">Uploading...</p>}
                </div>
              </Card>
            </TabsContent>
          </Tabs>
        </div>
      }
    />
  )
}
