import { useState } from 'react'
import { cn } from '@shared/lib/cn'
import { ShieldCheck, Scale, BadgeCheck, Bot, GitBranch, CheckCircle, AlertTriangle, XCircle } from 'lucide-react'
import { Badge } from '@shared/ui/Badge'
import { Progress } from '@shared/ui/Progress'

export interface TrustEvidence {
  id: string
  label: string
  status: 'verified' | 'warning' | 'failed'
  detail: string
}

interface TrustPanelProps {
  widgetId: string
  widgetTitle: string
  confidence?: number
  evidence?: TrustEvidence[]
  agentRuns?: { agent: string; status: string; duration: string }[]
  className?: string
}

const STATUS_ICONS = { verified: CheckCircle, warning: AlertTriangle, failed: XCircle, running: AlertTriangle, completed: CheckCircle }
const STATUS_COLORS = { verified: 'text-green-500', warning: 'text-amber-500', failed: 'text-red-500', running: 'text-blue-500', completed: 'text-green-500' }

const PANEL_TABS = [
  { id: 'evidence', label: 'Evidence', icon: Scale },
  { id: 'confidence', label: 'Confidence', icon: BadgeCheck },
  { id: 'agents', label: 'Agents', icon: Bot },
  { id: 'version', label: 'Version', icon: GitBranch },
]

export function TrustPanel({ widgetId, widgetTitle, confidence = 92, evidence = [], agentRuns = [], className }: TrustPanelProps) {
  const [open, setOpen] = useState(false)
  const [activeTab, setActiveTab] = useState('evidence')

  return (
    <div className={cn('border-t border-gray-100 dark:border-gray-800', className)}>
      <button
        type="button"
        onClick={() => setOpen(!open)}
        className="flex w-full items-center gap-2 px-4 py-2 text-[11px] font-medium text-gray-500 hover:bg-gray-50 hover:text-gray-700 dark:text-gray-400 dark:hover:bg-gray-800/30 dark:hover:text-gray-300 transition-colors"
      >
        <ShieldCheck size={12} className="text-green-500" />
        <span>Trust & Evidence</span>
        <Badge variant="outline" className="ml-auto text-[10px]">{confidence}% confidence</Badge>
      </button>

      {open && (
        <div className="border-t border-gray-50 bg-gray-50/50 px-4 py-3 dark:border-gray-800 dark:bg-gray-800/20">
          <div className="flex gap-0.5 mb-3">
            {PANEL_TABS.map((tab) => {
              const Icon = tab.icon
              return (
                <button
                  key={tab.id}
                  type="button"
                  onClick={() => setActiveTab(tab.id)}
                  className={cn(
                    'flex items-center gap-1 rounded-md px-2 py-1 text-[10px] font-medium transition-colors',
                    activeTab === tab.id
                      ? 'bg-white text-gray-900 shadow-sm dark:bg-gray-800 dark:text-white'
                      : 'text-gray-500 hover:text-gray-700 dark:text-gray-400',
                  )}
                >
                  <Icon size={10} />
                  {tab.label}
                </button>
              )
            })}
          </div>

          {activeTab === 'evidence' && (
            <div className="space-y-1">
              {evidence.length === 0 ? (
                <p className="text-[11px] text-gray-400 italic">No evidence records</p>
              ) : (
                evidence.map((ev) => {
                  const Icon = STATUS_ICONS[ev.status]
                  return (
                    <div key={ev.id} className="flex items-start gap-2">
                      <Icon size={11} className={cn('mt-0.5 shrink-0', STATUS_COLORS[ev.status])} />
                      <div>
                        <p className="text-[11px] font-medium text-gray-700 dark:text-gray-300">{ev.label}</p>
                        <p className="text-[10px] text-gray-400">{ev.detail}</p>
                      </div>
                    </div>
                  )
                })
              )}
            </div>
          )}

          {activeTab === 'confidence' && (
            <div>
              <div className="flex items-center justify-between mb-1">
                <span className="text-[11px] text-gray-600 dark:text-gray-400">Overall confidence</span>
                <span className="text-xs font-bold text-gray-900 dark:text-white">{confidence}%</span>
              </div>
              <Progress value={confidence} className="h-1.5" />
              <p className="mt-1 text-[10px] text-gray-400">
                widget: {widgetTitle} · id: {widgetId}
              </p>
            </div>
          )}

          {activeTab === 'agents' && (
            <div className="space-y-1">
              {agentRuns.length === 0 ? (
                <p className="text-[11px] text-gray-400 italic">No agent runs</p>
              ) : (
                agentRuns.map((run, i) => {
                  const Icon = STATUS_ICONS[run.status as keyof typeof STATUS_ICONS] ?? CheckCircle
                  return (
                    <div key={i} className="flex items-center justify-between">
                      <div className="flex items-center gap-1.5">
                        <Icon size={10} className={STATUS_COLORS[run.status as keyof typeof STATUS_COLORS]} />
                        <span className="text-[11px] text-gray-600 dark:text-gray-400">{run.agent}</span>
                      </div>
                      <span className="text-[10px] text-gray-400">{run.duration}</span>
                    </div>
                  )
                })
              )}
            </div>
          )}

          {activeTab === 'version' && (
            <p className="text-[11px] text-gray-400">
              Widget v1.0.0 · Data: live · Refresh: auto
            </p>
          )}
        </div>
      )}
    </div>
  )
}
