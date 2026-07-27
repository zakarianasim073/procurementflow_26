import { useState } from 'react'
import { Settings, User, Bell, Key, Palette, AlertCircle } from 'lucide-react'
import { ScreenTemplate } from '@layouts/index'
import { fetchJson } from '@entities/sharedApi'

export function SettingsPage() {
  const [activeTab, setActiveTab] = useState<'profile' | 'notifications' | 'api-keys' | 'theme'>('profile')
  const [saveStatus, setSaveStatus] = useState<'idle' | 'saving' | 'success' | 'error'>('idle')

  const tabs = [
    { id: 'profile', label: 'Profile', icon: User },
    { id: 'notifications', label: 'Notifications', icon: Bell },
    { id: 'api-keys', label: 'API Keys', icon: Key },
    { id: 'theme', label: 'Theme', icon: Palette },
  ]

  return (
    <ScreenTemplate
      header={
        <div className="flex items-center gap-3">
          <Settings className="h-6 w-6 text-blue-600" />
          <div>
            <h1 className="text-2xl font-bold text-gray-900 dark:text-white">Settings</h1>
            <p className="mt-0.5 text-sm text-gray-500 dark:text-gray-400">Manage your account and preferences</p>
          </div>
        </div>
      }
      primary={
        <div className="grid gap-6 lg:grid-cols-4">
          {/* Tab Navigation */}
          <div className="lg:col-span-1">
            <nav className="space-y-1">
              {tabs.map((tab) => {
                const Icon = tab.icon
                return (
                  <button
                    key={tab.id}
                    onClick={() => setActiveTab(tab.id as any)}
                    className={`flex w-full items-center gap-3 rounded-lg px-4 py-2 text-sm font-medium transition-colors ${
                      activeTab === tab.id
                        ? 'bg-blue-50 text-blue-600 dark:bg-blue-950/30 dark:text-blue-400'
                        : 'text-gray-600 hover:bg-gray-50 dark:text-gray-400 dark:hover:bg-gray-800'
                    }`}
                  >
                    <Icon size={18} />
                    {tab.label}
                  </button>
                )
              })}
            </nav>
          </div>

          {/* Content Area */}
          <div className="lg:col-span-3">
            <div className="rounded-xl border border-gray-200 bg-white p-6 dark:border-gray-800 dark:bg-gray-900">
              {/* Profile Tab */}
              {activeTab === 'profile' && (
                <div className="space-y-6">
                  <div>
                    <label className="block text-sm font-medium text-gray-900 dark:text-white">Full Name</label>
                    <input
                      id="fullName"
                      type="text"
                      defaultValue=""
                      className="mt-2 w-full rounded-lg border border-gray-300 bg-white px-4 py-2 text-sm text-gray-900 placeholder-gray-500 dark:border-gray-600 dark:bg-gray-800 dark:text-white"
                      placeholder="Your name"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-900 dark:text-white">Email</label>
                    <input
                      type="email"
                      defaultValue=""
                      disabled
                      className="mt-2 w-full rounded-lg border border-gray-300 bg-gray-50 px-4 py-2 text-sm text-gray-500 dark:border-gray-600 dark:bg-gray-800 dark:text-gray-400"
                    />
                    <p className="mt-1 text-xs text-gray-500">Email is managed by your identity provider</p>
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-900 dark:text-white">Organization</label>
                    <input
                      id="orgName"
                      type="text"
                      defaultValue=""
                      className="mt-2 w-full rounded-lg border border-gray-300 bg-white px-4 py-2 text-sm text-gray-900 dark:border-gray-600 dark:bg-gray-800 dark:text-white"
                      placeholder="Your organization"
                    />
                  </div>
                  <div className="flex items-center gap-3">
                    <button
                      onClick={async () => {
                        setSaveStatus('saving')
                        try {
                          await fetchJson('/api/v2/intelligence/user/settings', {
                            method: 'PUT',
                            body: JSON.stringify({
                              full_name: (document.getElementById('fullName') as HTMLInputElement)?.value ?? '',
                              organization: (document.getElementById('orgName') as HTMLInputElement)?.value ?? '',
                            }),
                            authed: true,
                          })
                          setSaveStatus('success')
                        } catch { setSaveStatus('error') }
                      }}
                      className="rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 dark:bg-blue-700 dark:hover:bg-blue-600"
                    >
                      Save Changes
                    </button>
                    {saveStatus === 'saving' && <span className="text-xs text-gray-500">Saving...</span>}
                    {saveStatus === 'success' && <span className="text-xs text-green-600">Saved</span>}
                    {saveStatus === 'error' && <span className="text-xs text-red-600">Failed</span>}
                  </div>
                </div>
              )}

              {/* Notifications Tab */}
              {activeTab === 'notifications' && (
                <div className="space-y-4">
                  <div className="flex items-center justify-between rounded-lg border border-gray-200 p-4 dark:border-gray-700">
                    <div>
                      <p className="font-medium text-gray-900 dark:text-white">Tender Alerts</p>
                      <p className="text-xs text-gray-500">Notifications for new matching tenders</p>
                    </div>
                    <input type="checkbox" defaultChecked className="rounded" />
                  </div>
                  <div className="flex items-center justify-between rounded-lg border border-gray-200 p-4 dark:border-gray-700">
                    <div>
                      <p className="font-medium text-gray-900 dark:text-white">Award Updates</p>
                      <p className="text-xs text-gray-500">Notifications when awards are published</p>
                    </div>
                    <input type="checkbox" defaultChecked className="rounded" />
                  </div>
                  <div className="flex items-center justify-between rounded-lg border border-gray-200 p-4 dark:border-gray-700">
                    <div>
                      <p className="font-medium text-gray-900 dark:text-white">Pipeline Changes</p>
                      <p className="text-xs text-gray-500">Notifications for updates to your pipeline</p>
                    </div>
                    <input type="checkbox" className="rounded" />
                  </div>
                  <div className="flex items-center gap-3">
                    <button
                      onClick={async () => {
                        setSaveStatus('saving')
                        try {
                          await fetchJson('/api/v2/intelligence/user/settings', {
                            method: 'PUT',
                            body: JSON.stringify({ notifications_enabled: true }),
                            authed: true,
                          })
                          setSaveStatus('success')
                        } catch { setSaveStatus('error') }
                      }}
                      className="rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 dark:bg-blue-700 dark:hover:bg-blue-600"
                    >
                      Save Preferences
                    </button>
                    {saveStatus === 'saving' && <span className="text-xs text-gray-500">Saving...</span>}
                    {saveStatus === 'success' && <span className="text-xs text-green-600">Saved</span>}
                    {saveStatus === 'error' && <span className="text-xs text-red-600">Failed</span>}
                  </div>
                </div>
              )}

              {/* API Keys Tab */}
              {activeTab === 'api-keys' && (
                <div className="space-y-4">
                  <div className="rounded-lg border border-amber-200 bg-amber-50 p-4 dark:border-amber-900 dark:bg-amber-950/30">
                    <div className="flex items-start gap-3">
                      <AlertCircle size={18} className="text-amber-600 dark:text-amber-400" />
                      <p className="text-sm text-amber-800 dark:text-amber-200">
                        Keep your API keys secret. Never share them or commit them to version control.
                      </p>
                    </div>
                  </div>
                  <div className="rounded-lg border border-gray-200 p-4 dark:border-gray-700">
                    <p className="mb-3 text-sm font-medium text-gray-900 dark:text-white">Active API Keys</p>
                    <p className="text-xs text-gray-500">No API keys created yet</p>
                    <button className="mt-3 rounded-lg bg-gray-100 px-4 py-2 text-sm font-medium text-gray-900 hover:bg-gray-200 dark:bg-gray-800 dark:text-white dark:hover:bg-gray-700">
                      Generate New Key
                    </button>
                  </div>
                </div>
              )}

              {/* Theme Tab */}
              {activeTab === 'theme' && (
                <div className="space-y-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-900 dark:text-white">Appearance</label>
                    <div className="mt-3 space-y-2">
                      <label className="flex items-center gap-3">
                        <input type="radio" name="theme" value="light" defaultChecked className="rounded-full" />
                        <span className="text-sm text-gray-700 dark:text-gray-300">Light</span>
                      </label>
                      <label className="flex items-center gap-3">
                        <input type="radio" name="theme" value="dark" className="rounded-full" />
                        <span className="text-sm text-gray-700 dark:text-gray-300">Dark</span>
                      </label>
                      <label className="flex items-center gap-3">
                        <input type="radio" name="theme" value="system" className="rounded-full" />
                        <span className="text-sm text-gray-700 dark:text-gray-300">System</span>
                      </label>
                    </div>
                  </div>
                  <button className="rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 dark:bg-blue-700 dark:hover:bg-blue-600">
                    Save Theme
                  </button>
                </div>
              )}

              {/* Save Status */}
              {saveStatus === 'success' && (
                <div className="mt-4 rounded-lg bg-green-50 p-3 text-sm text-green-800 dark:bg-green-950/30 dark:text-green-200">
                  ✓ Changes saved successfully
                </div>
              )}
              {saveStatus === 'error' && (
                <div className="mt-4 rounded-lg bg-red-50 p-3 text-sm text-red-800 dark:bg-red-950/30 dark:text-red-200">
                  ✗ Failed to save changes
                </div>
              )}
            </div>
          </div>
        </div>
      }
    />
  )
}
