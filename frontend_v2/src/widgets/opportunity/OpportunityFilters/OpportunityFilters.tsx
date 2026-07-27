import { FilterSelect, FilterInput } from '@widgets/shared'
import { useAgencies } from '@hooks/opportunity'
import { useCategories } from '@hooks/index'

interface OpportunityFiltersProps {
  searchQuery: string
  onSearchChange: (v: string) => void
  agencyFilter: string
  onAgencyChange: (v: string) => void
  categoryFilter: string
  onCategoryChange: (v: string) => void
}

const FALLBACK_AGENCIES = ['BWDB', 'LGED', 'RHD', 'PWD', 'REB', 'WASA', 'City Corp']
const FALLBACK_CATEGORIES = ['Civil', 'Electrical', 'Mechanical', 'ICT', 'Supply', 'Consultancy']

export function OpportunityFilters({ searchQuery, onSearchChange, agencyFilter, onAgencyChange, categoryFilter, onCategoryChange }: OpportunityFiltersProps) {
  const { data: agenciesData } = useAgencies()
  const { data: categoriesData } = useCategories()

  const agencies = agenciesData?.agencies?.length
    ? agenciesData.agencies.map((a) => a.name)
    : FALLBACK_AGENCIES

  const categoryItems = categoriesData ?? []
  const categories = categoryItems.length >= 3
    ? categoryItems.map((c) => c.label)
    : FALLBACK_CATEGORIES

  return (
    <div className="flex flex-wrap items-center gap-2">
      <FilterSelect label="Agency" value={agencyFilter} onChange={(e) => onAgencyChange(e.target.value)}>
        <option value="">All agencies</option>
        {agencies.map((a) => <option key={a} value={a}>{a}</option>)}
      </FilterSelect>
      <FilterSelect label="Category" value={categoryFilter} onChange={(e) => onCategoryChange(e.target.value)}>
        <option value="">All categories</option>
        {categories.map((c) => <option key={c} value={c}>{c}</option>)}
      </FilterSelect>
      <FilterInput value={searchQuery} onChange={onSearchChange} placeholder="Search tenders..." />
    </div>
  )
}
