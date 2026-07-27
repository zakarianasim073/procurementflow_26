import { exportRoiPdf } from '@entities/index'

export async function exportRoiDownload(params?: { period?: string }): Promise<void> {
  const blob = await exportRoiPdf(params)
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `roi-report${params?.period ? `-${params.period}` : ''}.json`
  document.body.appendChild(a)
  a.click()
  document.body.removeChild(a)
  URL.revokeObjectURL(url)
}
