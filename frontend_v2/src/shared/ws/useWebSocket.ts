import { useEffect, useRef, useState, useCallback } from 'react'
import { getAuthToken } from '@entities/authToken'

export interface WebSocketMessage {
  type: string
  data: Record<string, unknown>
}

export function useWebSocket(path: string, onMessage?: (msg: WebSocketMessage) => void) {
  const [connected, setConnected] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const wsRef = useRef<WebSocket | null>(null)

  useEffect(() => {
    const token = getAuthToken()
    if (!token) {
      setError('No authentication token found')
      return
    }

    const protocol = window.location.protocol === 'https:' ? 'wss' : 'ws'
    const wsUrl = `${protocol}://${window.location.host}/api/ws${path}?token=${encodeURIComponent(token)}`

    try {
      const ws = new WebSocket(wsUrl)

      ws.onopen = () => {
        setConnected(true)
        setError(null)
      }

      ws.onmessage = (event) => {
        try {
          const message = JSON.parse(event.data) as WebSocketMessage
          onMessage?.(message)
        } catch (err) {
          console.error('Failed to parse WebSocket message:', err)
        }
      }

      ws.onerror = () => {
        setError('WebSocket connection error')
      }

      ws.onclose = () => {
        setConnected(false)
      }

      wsRef.current = ws
    } catch (err) {
      setError(`Failed to connect: ${err instanceof Error ? err.message : String(err)}`)
    }

    return () => {
      if (wsRef.current) {
        wsRef.current.close()
      }
    }
  }, [path, onMessage])

  const send = useCallback((message: WebSocketMessage) => {
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify(message))
    }
  }, [])

  return { connected, error, send }
}
