# EvidencePanel Component Contract

**Package**: `widgets/ai`  
**Type**: AI Evidence Display Component  
**Stability**: Stable  

---

## Purpose

Displays AI reasoning evidence, confidence factors, and supporting data for decisions. Used in executive reports, bid recommendations, and compliance reviews to provide transparency into AI-driven insights.

---

## Props

```typescript
interface EvidencePanelProps {
  /** Evidence data */
  evidence: {
    /** Overall confidence score (0-1) */
    confidence: number;
    /** Confidence level label */
    confidenceLevel: 'Very High' | 'High' | 'Medium' | 'Low' | 'Very Low';
    /** Supporting factors */
    factors: EvidenceFactor[];
    /** Contradicting factors */
    contradictions?: EvidenceFactor[];
    /** Data sources */
    sources: EvidenceSource[];
    /** Methodology description */
    methodology?: string;
    /** Limitations */
    limitations?: string[];
  };
  /** Panel variant */
  variant?: 'default' | 'compact' | 'detailed' | 'inline';
  /** Show confidence badge */
  showConfidenceBadge?: boolean;
  /** Expandable sections */
  expandable?: boolean;
  /** Custom className */
  className?: string;
}

interface EvidenceFactor {
  id: string;
  label: string;
  description: string;
  weight: number; // 0-1, contribution to confidence
  impact: 'positive' | 'negative' | 'neutral';
  data?: {
    value: string | number;
    reference: string;
    timestamp: string;
  };
}

interface EvidenceSource {
  id: string;
  name: string;
  type: 'database' | 'model' | 'api' | 'manual' | 'historical';
  reliability: number; // 0-1
  lastUpdated: string;
  recordCount?: number;
}
```

---

## Slots

| Slot | Required | Description |
|------|----------|-------------|
| `header` | No | Custom confidence display |
| `factors` | No | Custom factor rendering |
| `sources` | No | Custom source list |
| `methodology` | No | Custom methodology display |

---

## State

| State | Trigger | Visual |
|-------|---------|--------|
| `default` | Initial | Full panel with all sections |
| `compact` | `variant='compact'` | Confidence badge + top 3 factors |
| `loading` | Evidence fetching | Skeleton for each section |
| `error` | Fetch failed | Alert with retry |
| `expanded` | `expandable` + click | All sections visible |
| `collapsed` | `expandable` + click | Summary only |

---

## Accessibility

- **Role**: `region` with `aria-label="AI Evidence: [confidence level] confidence"`
- **Confidence**: `aria-label="Confidence: [value]%"`
- **Factors**: `aria-label="Factor: [label], weight [weight], impact [impact]"`
- **Expandable**: `aria-expanded` on toggle button
- **Keyboard**: Tab through factors, Enter expands

---

## Loading

- **Skeleton**: Confidence ring + factor list skeletons
- **Delay**: 150ms

---

## Errors

- **Missing Evidence**: "No evidence available for this decision"
- **Low Confidence**: Warning banner "Confidence below threshold — review recommended"

---

## Keyboard

| Key | Action |
|-----|--------|
| `Tab` | Navigate factors/sources |
| `Enter` / `Space` | Toggle expand |
| `Escape` | Collapse |

---

## Mobile

- **< 640px**: Stacked layout, collapsible sections
- **Confidence**: Large badge at top
- **Factors**: Accordion list

---

## Permissions

| Role | View |
|------|------|
| All authenticated | ✅ |

---

## Telemetry

| Event | Properties |
|-------|------------|
| `evidence_panel_view` | `variant`, `confidence`, `factor_count` |
| `evidence_expand` | `section` |
| `evidence_source_click` | `source_id`, `type` |

---

## React Query

```typescript
const { data } = useQuery({
  queryKey: executiveKeys.report(tenderId),
  select: (report) => report.report.model_intelligence.evidence
});
```

---

## Dependencies

- `ConfidenceBadge` (for confidence display)
- `FactorBar` (visual weight representation)
- `SourceBadge` (for source reliability)
- `ExpandableSection` (for collapsible content)
- `lucide-react`: `Shield`, `CheckCircle`, `XCircle`, `Info`, `AlertTriangle`, `Database`, `Brain`, `FileText`, `Clock`, `Expand`, `ChevronDown`

---

## Confidence Level Mapping

| Score Range | Level | Color | Icon |
|-------------|-------|-------|------|
| 0.90 - 1.00 | Very High | Green | `Shield` |
| 0.75 - 0.89 | High | Blue | `CheckCircle` |
| 0.60 - 0.74 | Medium | Yellow | `Info` |
| 0.40 - 0.59 | Low | Orange | `AlertTriangle` |
| 0.00 - 0.39 | Very Low | Red | `XCircle` |

---

## Factor Visualization

```
Positive Factor (weight: 0.35)
├── Label: "Strong SOR match rate"
├── Description: "78% of BOQ items matched SOR within 5%"
├── Weight Bar: ████████████░░░░░░░░░░ 35%
├── Impact: 🟢 Positive
└── Data: "78% match rate" (SOR Service, 2026-07-21)

Negative Factor (weight: 0.20)
├── Label: "High competitor density"
├── Description: "4 established contractors in zone"
├── Weight Bar: ██████░░░░░░░░░░░░░░░░ 20%
├── Impact: 🔴 Negative
└── Data: "4 competitors" (Intelligence DB, 2026-07-20)
```

---

## Future Extensions

- [ ] Evidence comparison (side-by-side)
- [ ] Counterfactual analysis ("What if factor X changed?")
- [ ] Evidence lineage graph
- [ ] Export evidence as PDF appendix
- [ ] Interactive weight adjustment