interface Peer {
  name: string
  winRate: number
  priceDelta: number
  ranking: 'above' | 'below'
}

interface PeerComparisonProps {
  you: { name: string; winRate: number; priceDelta: number }
  peers?: Peer[]
}

export function PeerComparison({
  you,
  peers = [
    { name: 'XYZ Corp', winRate: 32, priceDelta: 5.1, ranking: 'below' },
    { name: 'DEF Ltd', winRate: 45, priceDelta: 2.1, ranking: 'above' },
  ],
}: PeerComparisonProps) {
  return (
    <div className="rounded-xl border border-gray-200 bg-white p-6 dark:border-gray-700 dark:bg-gray-800">
      <h3 className="mb-4 text-sm font-semibold text-gray-900 dark:text-white">Peer Comparison</h3>
      <div className="space-y-3">
        <div className="rounded-lg bg-blue-50 p-3 dark:bg-blue-900/30">
          <div className="flex items-center justify-between">
            <span className="text-sm font-semibold text-blue-900 dark:text-blue-300">You ({you.name})</span>
            <span className="text-sm font-semibold text-blue-900 dark:text-blue-300">{you.winRate}% win rate</span>
          </div>
          <p className="mt-1 text-xs text-blue-700 dark:text-blue-400">Avg bid delta: +{you.priceDelta.toFixed(1)}%</p>
        </div>
        {peers.map((peer) => (
          <div
            key={peer.name}
            className={`rounded-lg p-3 ${
              peer.ranking === 'above'
                ? 'bg-green-50 dark:bg-green-900/30'
                : 'bg-gray-50 dark:bg-gray-900/30'
            }`}
          >
            <div className="flex items-center justify-between">
              <span className={`text-sm font-medium ${peer.ranking === 'above' ? 'text-green-900 dark:text-green-300' : 'text-gray-900 dark:text-gray-300'}`}>
                {peer.name}
              </span>
              <span className={`text-sm font-semibold ${peer.ranking === 'above' ? 'text-green-900 dark:text-green-300' : 'text-gray-900 dark:text-gray-300'}`}>
                {peer.winRate}% win rate
              </span>
            </div>
            <p className={`mt-1 text-xs ${peer.ranking === 'above' ? 'text-green-700 dark:text-green-400' : 'text-gray-700 dark:text-gray-400'}`}>
              Avg bid delta: +{peer.priceDelta.toFixed(1)}% {peer.ranking === 'above' ? '⭐ (more aggressive)' : ''}
            </p>
          </div>
        ))}
      </div>
    </div>
  )
}
