import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { ArrowLeft, Shield, CheckCircle, XCircle, AlertTriangle, RefreshCw } from 'lucide-react'
import { cn } from '@shared/lib/cn'
import { Tabs, TabsList, TabsTrigger, TabsContent } from '@shared/ui/Tabs'
import { Button } from '@shared/ui/Button'
import { Input } from '@shared/ui/Input'
import { Card } from '@shared/ui/Card'
import { Badge } from '@shared/ui/Badge'
import { Skeleton } from '@shared/ui/Skeleton'
import { EmptyState } from '@shared/ui/EmptyState'
import { ScreenTemplate } from '@layouts/index'
import { useComplianceCheck, useTdsCriteria, useRunComplianceCheck } from '@hooks/index'

function StatusIcon({ status }: { status: string }) {
  if (status === 'pass') return <CheckCircle className="h-5 w-5 text-green-500" />
  if (status === 'fail') return <XCircle className="h-5 w-5 text-red-500" />
  return <AlertTriangle className="h-5 w-5 text-yellow-500" />
}

export function CompliancePage() {
  const navigate = useNavigate()
  const [tenderId, setTenderId] = useState('')
  const [activeTab, setActiveTab] = useState<'rules' | 'tds'>('rules')

  const { data: compliance, isLoading } = useComplianceCheck(tenderId)
  const { data: tds } = useTdsCriteria(tenderId)
  const runCheck = useRunComplianceCheck()

  return (
    <ScreenTemplate
      header={
        <div className="flex items-center gap-3">
          <button onClick={() => navigate('/tender')} className="rounded-lg p-1.5 text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-800">
            <ArrowLeft size={18} />
          </button>
          <div>
            <h1 className="text-lg font-semibold text-gray-900 dark:text-white">Compliance Check</h1>
            <p className="text-sm text-gray-500 dark:text-gray-400">PPR 2025 compliance and TDS criteria verification</p>
          </div>
        </div>
      }
      primary={
        <div className="space-y-6">
          <Card className="p-4">
            <div className="flex flex-wrap items-end gap-4">
              <Input
                label="Tender ID"
                value={tenderId}
                onChange={(e) => setTenderId(e.target.value)}
                placeholder="e.g. 1298004"
                className="w-48"
              />
              <Button onClick={() => runCheck.mutate(tenderId)} disabled={!tenderId || runCheck.isPending}>
                <RefreshCw className={cn('h-4 w-4 mr-2', runCheck.isPending && 'animate-spin')} />
                {runCheck.isPending ? 'Checking...' : 'Run Check'}
              </Button>
            </div>
          </Card>

          {compliance && (
            <Card className="p-4">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm font-medium text-gray-900 dark:text-white">Overall Status</p>
                  <p className="text-xs text-gray-500 dark:text-gray-400">Score: {compliance.score}/100</p>
                </div>
                <Badge tone={compliance.overall_status === 'compliant' ? 'success' : compliance.overall_status === 'partial' ? 'warning' : 'danger'}>
                  {compliance.overall_status}
                </Badge>
              </div>
            </Card>
          )}

          <Tabs value={activeTab} onValueChange={(v) => setActiveTab(v as typeof activeTab)}>
            <TabsList>
              <TabsTrigger value="rules">
                <Shield className="h-4 w-4 mr-2" />
                PPR Rules
              </TabsTrigger>
              <TabsTrigger value="tds">
                <CheckCircle className="h-4 w-4 mr-2" />
                TDS Criteria
              </TabsTrigger>
            </TabsList>

            <TabsContent value="rules">
              {isLoading ? (
                <div className="space-y-3">
                  {Array.from({ length: 4 }).map((_, i) => <Skeleton key={i} className="h-20 w-full rounded-xl" />)}
                </div>
              ) : !compliance ? (
                <EmptyState title="No compliance data" description="Enter a tender ID and run a compliance check." />
              ) : (
                <div className="space-y-3">
                  {compliance.rules.map((rule) => (
                    <Card key={rule.rule_id} className="p-4">
                      <div className="flex items-start gap-3">
                        <StatusIcon status={rule.status} />
                        <div className="flex-1">
                          <div className="flex items-center gap-2">
                            <span className="font-mono text-xs text-gray-500">{rule.rule_code}</span>
                            <span className="text-sm font-medium text-gray-900 dark:text-white">{rule.title}</span>
                          </div>
                          <p className="mt-1 text-xs text-gray-500 dark:text-gray-400">{rule.description}</p>
                          {rule.details && (
                            <p className="mt-2 text-xs text-gray-600 dark:text-gray-300">{rule.details}</p>
                          )}
                        </div>
                        <Badge tone={rule.status === 'pass' ? 'success' : rule.status === 'fail' ? 'danger' : 'warning'}>
                          {rule.status}
                        </Badge>
                      </div>
                    </Card>
                  ))}
                </div>
              )}
            </TabsContent>

            <TabsContent value="tds">
              {!tds ? (
                <EmptyState title="No TDS criteria" description="Enter a tender ID to view TDS criteria." />
              ) : (
                <Card className="p-4">
                  <h3 className="mb-4 text-sm font-semibold text-gray-700 dark:text-gray-300">Technical Data Sheet Criteria</h3>
                  <div className="space-y-3">
                    {Object.entries(tds).map(([key, value]) => (
                      <div key={key} className="flex justify-between rounded-lg border border-gray-100 bg-gray-50 p-3 dark:border-gray-700 dark:bg-gray-800/60">
                        <span className="text-sm text-gray-600 dark:text-gray-400">
                          {key.replace(/_/g, ' ').replace(/\b\w/g, (l) => l.toUpperCase())}
                        </span>
                        <span className="text-sm font-medium text-gray-900 dark:text-white">{value}</span>
                      </div>
                    ))}
                  </div>
                </Card>
              )}
            </TabsContent>
          </Tabs>
        </div>
      }
    />
  )
}
