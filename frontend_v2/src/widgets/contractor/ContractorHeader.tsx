import { Badge } from '@shared/ui/Badge'

interface ContractorHeaderProps {
  name: string
  registrationId: string
  status: 'active' | 'inactive' | 'suspended'
  yearsOperating: number
  ppr2025Eligible: boolean
  activeInEgpLast30d: boolean
}

export function ContractorHeader({
  name,
  registrationId,
  status,
  yearsOperating,
  ppr2025Eligible,
  activeInEgpLast30d,
}: ContractorHeaderProps) {
  const statusColors = {
    active: 'bg-green-50 text-green-700 dark:bg-green-900/30 dark:text-green-400',
    inactive: 'bg-gray-50 text-gray-700 dark:bg-gray-900/30 dark:text-gray-400',
    suspended: 'bg-red-50 text-red-700 dark:bg-red-900/30 dark:text-red-400',
  }

  return (
    <div className="rounded-xl border border-gray-200 bg-white p-6 dark:border-gray-700 dark:bg-gray-800">
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white">{name}</h1>
          <p className="text-sm text-gray-600 dark:text-gray-400">Registration: {registrationId}</p>
        </div>
        <div className="flex gap-2">
          <Badge className={statusColors[status]}>{status === 'active' ? '✓ Active' : status}</Badge>
          {ppr2025Eligible && <Badge className="bg-blue-50 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400">✓ PPR2025 Eligible</Badge>}
        </div>
      </div>

      <div className="mt-4 grid grid-cols-3 gap-4">
        <div>
          <p className="text-xs font-medium text-gray-600 dark:text-gray-400">Years Operating</p>
          <p className="text-lg font-semibold text-gray-900 dark:text-white">{yearsOperating}</p>
        </div>
        <div>
          <p className="text-xs font-medium text-gray-600 dark:text-gray-400">Active in e-GP</p>
          <p className="text-lg font-semibold text-gray-900 dark:text-white">{activeInEgpLast30d ? 'Last 30d' : 'Inactive'}</p>
        </div>
        <div>
          <p className="text-xs font-medium text-gray-600 dark:text-gray-400">Overall Status</p>
          <p className="text-lg font-semibold text-gray-900 dark:text-white">Stable</p>
        </div>
      </div>
    </div>
  )
}
