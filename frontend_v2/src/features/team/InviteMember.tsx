import { useState } from 'react'
import { useInviteTeamMember } from '@hooks/index'

interface Props {
  onSuccess?: () => void
  onCancel?: () => void
}

export function InviteMember({ onSuccess, onCancel }: Props) {
  const [email, setEmail] = useState('')
  const [fullName, setFullName] = useState('')
  const [role, setRole] = useState<'admin' | 'member' | 'viewer'>('member')
  const { mutate: inviteMember, isPending } = useInviteTeamMember()

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()

    if (!email || !email.includes('@')) {
      alert('Please enter a valid email address')
      return
    }
    if (!fullName.trim()) {
      alert('Please enter the member’s full name')
      return
    }

    inviteMember(
      { email, full_name: fullName, role },
      {
        onSuccess: () => {
          setEmail('')
          setFullName('')
          setRole('member')
          onSuccess?.()
        },
        onError: (error) => {
          alert(`Invitation failed: ${error instanceof Error ? error.message : 'Unknown error'}`)
        },
      },
    )
  }

  return (
    <div className="rounded-lg border border-gray-200 bg-white p-4 dark:border-gray-800 dark:bg-gray-900">
      <form onSubmit={handleSubmit} className="space-y-4">
        <div>
          <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
            Email Address
          </label>
          <input
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            placeholder="colleague@company.com"
            disabled={isPending}
            className="w-full rounded border border-gray-300 px-3 py-2 dark:border-gray-600 dark:bg-gray-800 disabled:opacity-50"
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
            Full Name
          </label>
          <input
            type="text"
            value={fullName}
            onChange={(e) => setFullName(e.target.value)}
            placeholder="Jane Doe"
            disabled={isPending}
            className="w-full rounded border border-gray-300 px-3 py-2 dark:border-gray-600 dark:bg-gray-800 disabled:opacity-50"
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
            Role
          </label>
          <select
            value={role}
            onChange={(e) => setRole(e.target.value as typeof role)}
            disabled={isPending}
            className="w-full rounded border border-gray-300 px-3 py-2 dark:border-gray-600 dark:bg-gray-800 disabled:opacity-50"
          >
            <option value="viewer">Viewer (Read-only)</option>
            <option value="member">Member (Read & edit)</option>
            <option value="admin">Admin (Full access)</option>
          </select>
          <p className="mt-1 text-xs text-gray-500 dark:text-gray-400">
            {role === 'viewer' && 'Can view tenders and documents'}
            {role === 'member' && 'Can view, create, and edit tenders and documents'}
            {role === 'admin' && 'Full access to all features and team management'}
          </p>
        </div>

        <div className="flex gap-2">
          <button
            type="submit"
            disabled={isPending || !email || !fullName}
            className="flex-1 px-4 py-2 rounded-lg bg-blue-600 text-white hover:bg-blue-700 disabled:opacity-50 font-medium"
          >
            {isPending ? 'Sending...' : 'Send Invitation'}
          </button>
          <button
            type="button"
            onClick={onCancel}
            disabled={isPending}
            className="px-4 py-2 rounded-lg border border-gray-300 text-gray-700 hover:bg-gray-50 dark:border-gray-600 dark:text-gray-300 dark:hover:bg-gray-800 disabled:opacity-50"
          >
            Cancel
          </button>
        </div>
      </form>
    </div>
  )
}
