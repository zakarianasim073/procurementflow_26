import { describe, expect, it } from 'vitest'
import { safeInternalPath } from './safeNavigation'

describe('safeInternalPath', () => {
  it('preserves same-origin application paths', () => {
    expect(safeInternalPath('/tender/123?tab=overview#evidence')).toBe('/tender/123?tab=overview#evidence')
  })

  it.each([
    'https://evil.example/phish',
    '//evil.example/phish',
    '/\\evil.example/phish',
    '\\\\evil.example\\phish',
    'javascript:alert(1)',
  ])('rejects unsafe redirect %s', value => {
    expect(safeInternalPath(value)).toBe('/executive')
  })
})
