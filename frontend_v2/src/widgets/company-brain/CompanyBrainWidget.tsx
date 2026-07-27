import { useState, useMemo } from 'react'
import { Building2, Shield, Search, RefreshCw, Edit3 } from 'lucide-react'
import { WidgetContainer, WidgetHeader, WidgetToolbar, ToolbarButton, WidgetTabs, WidgetContent, WidgetFooter, TrustPanel, AiDrawer, WidgetActions } from '@widgets/shared'
import { cn } from '@shared/lib/cn'
import { Badge } from '@shared/ui/Badge'
import { Progress } from '@shared/ui/Progress'
import { useContractorProfile, useExperience } from '@hooks/contractor'

const BRAIN_TABS = [
  { id: 'profile', label: 'Profile' },
  { id: 'experience', label: 'Experience' },
  { id: 'finance', label: 'Finance' },
  { id: 'risk', label: 'Risk' },
]

const fmt = (n: number) => n >= 1e7 ? `৳${(n / 1e7).toFixed(1)} Cr` : n >= 1e5 ? `৳${(n / 1e5).toFixed(1)}L` : `৳${n.toLocaleString()}`

export interface CompanyBrainWidgetProps {
  companyId?: string
}

export function CompanyBrainWidget({ companyId }: CompanyBrainWidgetProps) {
  const [activeTab, setActiveTab] = useState('profile')
  const [drawerOpen, setDrawerOpen] = useState(false)

  const { data: profile, isLoading: profileLoading } = useContractorProfile(companyId)
  const { data: experience, isLoading: expLoading } = useExperience(companyId)

  const isLoading = profileLoading || expLoading

  const profileSections = useMemo(() => {
    if (!profile) return []
    return [
      { label: 'Company Name', value: profile.name },
      { label: 'Years Operating', value: `${profile.years_operating} years` },
      { label: 'Registration', value: profile.registration_id },
      { label: 'Status', value: profile.status },
      { label: 'PPR2025 Eligible', value: profile.ppr2025_eligible ? 'Yes' : 'No' },
      { label: 'Active in e-GP (30d)', value: profile.active_in_egp_last_30d ? 'Yes' : 'No' },
      { label: 'Annual Turnover', value: fmt(profile.financial.annual_turnover) },
      { label: 'Cash Position', value: fmt(profile.financial.cash_position) },
    ]
  }, [profile])

  const experienceByAgency = useMemo(() => {
    if (!experience) return []
    return experience.by_category.map((e) => ({
      agency: e.category,
      contracts: e.projects_count,
      value: fmt(e.avg_value),
      rating: Math.min(Math.round((e.projects_count / 5) * 50 + 50), 100),
    }))
  }, [experience])

  const riskLevels = useMemo(() => {
    if (!profile?.risk_profile) return []
    const rp = profile.risk_profile
    return [
      { area: 'Compliance Risk', level: rp.compliance_risk, detail: '', color: rp.compliance_risk === 'low' ? 'text-green-500' : rp.compliance_risk === 'medium' ? 'text-amber-500' : 'text-red-500' },
      { area: 'Market Risk', level: rp.market_risk, detail: '', color: rp.market_risk === 'low' ? 'text-green-500' : rp.market_risk === 'medium' ? 'text-amber-500' : 'text-red-500' },
      { area: 'Financial Risk', level: rp.financial_risk, detail: '', color: rp.financial_risk === 'low' ? 'text-green-500' : rp.financial_risk === 'medium' ? 'text-amber-500' : 'text-red-500' },
      { area: 'Operational Risk', level: rp.operational_risk, detail: '', color: rp.operational_risk === 'low' ? 'text-green-500' : rp.operational_risk === 'medium' ? 'text-amber-500' : 'text-red-500' },
    ]
  }, [profile])

  const riskFlags = profile?.risk_profile?.flags ?? []
  const overallRisk = profile?.risk_profile?.overall_risk ?? 'low'

  return (
    <WidgetContainer>
      <WidgetHeader title="Company Brain" subtitle="360° organizational intelligence" icon={<Building2 size={16} />} />
      <WidgetToolbar>
        <ToolbarButton icon={<Search size={14} />} label="Search" />
        <ToolbarButton icon={<Edit3 size={14} />} label="Edit" />
        <ToolbarButton icon={<RefreshCw size={14} />} label="Sync" />
      </WidgetToolbar>
      <WidgetTabs tabs={BRAIN_TABS} activeTab={activeTab} onTabChange={setActiveTab} />
      <WidgetContent>
        {isLoading ? (
          <div className="flex items-center justify-center h-32"><p className="text-sm text-gray-500">Loading company data...</p></div>
        ) : (
        <>
        {activeTab === 'profile' && (
          <div className="divide-y divide-gray-50 dark:divide-gray-800/50">
            {profileSections.map((s) => (
              <div key={s.label} className="flex items-center justify-between px-4 py-2.5">
                <span className="text-xs text-gray-500 dark:text-gray-400">{s.label}</span>
                <span className="text-xs font-medium text-gray-900 dark:text-white">{s.value}</span>
              </div>
            ))}
          </div>
        )}
        {activeTab === 'experience' && (
          <div className="divide-y divide-gray-50 dark:divide-gray-800/50">
            {experienceByAgency.map((e) => (
              <div key={e.agency} className="px-4 py-3">
                <div className="flex items-center justify-between mb-1.5">
                  <div className="flex items-center gap-2">
                    <span className="text-xs font-medium text-gray-900 dark:text-white">{e.agency}</span>
                    <Badge variant="outline" className="text-[10px]">{e.contracts} contracts</Badge>
                  </div>
                  <span className="text-xs font-semibold text-gray-700 dark:text-gray-300">{e.value}</span>
                </div>
                <div className="flex items-center gap-2">
                  <Progress value={e.rating} className="h-1.5 flex-1" />
                  <span className="text-[11px] font-medium text-gray-500">{e.rating}%</span>
                </div>
              </div>
            ))}
          </div>
        )}
        {activeTab === 'finance' && profile && (
          <div className="grid grid-cols-2 gap-3 p-4">
            {[
              { label: 'Annual Revenue', value: fmt(profile.financial.annual_turnover) },
              { label: 'Cash Position', value: fmt(profile.financial.cash_position) },
              { label: 'Debt Ratio', value: profile.financial.debt_ratio.toFixed(2) },
              { label: 'Financial Trend', value: profile.financial.financial_trend },
            ].map((f) => (
              <div key={f.label} className="rounded-lg border border-gray-100 p-3 dark:border-gray-800">
                <p className="text-[11px] text-gray-500 dark:text-gray-400">{f.label}</p>
                <p className="mt-0.5 text-sm font-bold text-gray-900 dark:text-white">{f.value}</p>
              </div>
            ))}
          </div>
        )}
        {activeTab === 'risk' && (
          <div className="space-y-3 p-4">
            {riskLevels.map((r) => (
              <div key={r.area} className="flex items-center justify-between rounded-lg border border-gray-100 p-3 dark:border-gray-800">
                <div>
                  <p className="text-xs font-medium text-gray-900 dark:text-white">{r.area}</p>
                  {riskFlags.filter(f => f.flag.includes(r.area.replace(' Risk', ''))).map((f, i) => (
                    <p key={i} className="text-[11px] text-gray-500">{f.recommendation}</p>
                  ))}
                </div>
                <span className={cn('text-xs font-semibold', r.color)}>{r.level}</span>
              </div>
            ))}
            {riskFlags.length > 0 && (
              <div className="rounded-lg border border-red-100 bg-red-50 p-3 dark:border-red-900 dark:bg-red-950/30">
                <p className="text-xs font-medium text-red-700 dark:text-red-400">Flags ({riskFlags.length})</p>
                {riskFlags.map((f, i) => (
                  <p key={i} className="text-[11px] text-red-600 dark:text-red-300 mt-1">{f.flag} — {f.recommendation}</p>
                ))}
              </div>
            )}
          </div>
        )}
        </>)}
      </WidgetContent>
      <WidgetActions onAiAction={() => setDrawerOpen(true)} aiLabel="Company Analysis" />
      <WidgetFooter>
        <div className="flex items-center justify-between text-[11px] text-gray-500">
          <span>{profile ? `${profile.name}` : 'Company Brain'}</span>
          <span className="flex items-center gap-1"><Shield size={12} /> Overall risk: {overallRisk}</span>
        </div>
      </WidgetFooter>
      <TrustPanel widgetId="company-brain" widgetTitle="Company Brain" confidence={91} evidence={[{ id: 'ev-1', label: 'Company data from procurement engine', status: 'verified', detail: 'All agencies' }]} />
      <AiDrawer open={drawerOpen} onClose={() => setDrawerOpen(false)} widgetTitle="Company Brain" />
    </WidgetContainer>
  )
}
