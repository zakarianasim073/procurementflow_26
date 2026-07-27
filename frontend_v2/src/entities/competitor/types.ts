export interface Competitor {
  competitor_id: string
  name: string
  win_rate: number
  total_bids: number
  total_wins: number
  avg_discount: number
  specialties: string[]
  agencies: string[]
  recent_activity: CompetitorActivity[]
}

export interface CompetitorActivity {
  tender_id: string
  title: string
  agency: string
  bid_amount: number
  status: 'submitted' | 'won' | 'lost' | 'pending'
  date: string
}

export interface CompetitorAnalysis {
  tender_id: string
  competitors: Competitor[]
  market_position: string
  threat_level: 'low' | 'medium' | 'high'
  recommendations: string[]
}
