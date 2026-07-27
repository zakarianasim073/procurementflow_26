# TrustPanel Component Contract

**Package**: `widgets/ai`  
**Type**: AI Trust Display Component  
**Stability**: Stable  

---

## Purpose

Displays trust indicators, confidence scores, and reasoning for AI-driven recommendations. Used in executive decision screens, bid recommendation panels, and compliance reviews to provide transparency into AI decision-making.

---

## Props

```typescript
interface TrustPanelProps {
  /** Trust assessment data */
  trust: {
    /** Overall trust score (0-1) */
    overallScore: number;
    /** Trust level label */
    level: 'High' | 'Medium' | 'Low' | 'Critical';
    /** Confidence breakdown */
    dimensions: TrustDimension[];
    /** Risk factors */
    risks: TrustRisk[];
    /** Assurances */
    assurances: TrustAssurance[];
    /** Last assessment timestamp */
    assessedAt: string;
    /** Assessor (agent/model) */
    assessor: string;
  };
  /** Panel variant */
  variant?: 'default' | 'compact' | 'card' | 'inline';
  /** Show detailed breakdown */
  showDetails?: boolean;
  /** Click handler for dimension/risk */
  onItemClick?: (item: TrustDimension | TrustRisk) => void;
  /** Custom className */
  className?: string;
}

interface TrustDimension {
  id: string;
  name: string;
  description: string;
  score: number; // 0-1
  weight: number; // contribution to overall
  status: 'pass' | 'warning' | 'fail';
  evidence?: string[];
}

interface TrustRisk {
  id: string;
  name: string;
  description: string;
  severity: 'low' | 'medium' | 'high' | 'critical';
  likelihood: number; // 0-1
  impact: number; // 0-1
  mitigation?: string;
}

interface TrustAssurance {
  id: string;
  name: string;
  description: string;
  verified: boolean;
  verificationMethod: 'automated' | 'manual' | 'third-party';
  evidence?: string;
}
```

---

## Slots

| Slot | Required | Description |
|------|----------|-------------|
| `header` | No | Custom trust score display |
| `dimensions` | No | Custom dimension rendering |
| `risks` | No | Custom risk list |
| `assurances` | No | Custom assurance list |
| `actions` | No | Action buttons (review, approve, escalate) |

---

## State

| State | Trigger | Visual |
|-------|---------|--------|
| `default` | Initial | Full panel with all dimensions |
| `compact` | `variant='compact'` | Score + top 3 risks |
| `loading` | Data fetching | Skeleton for each section |
| `error` | Fetch failed | Alert with retry |
| `expanded` | `showDetails=true` | All sections visible |
| `critical` | `level='Critical'` | Red border, pulse animation |

---

## Accessibility

- **Role**: `region` with `aria-label="Trust Assessment: [level]"`
- **Score**: `aria-valuenow` on progress indicators
- **Dimensions**: `aria-label="[name]: [score]%, [status]"`
- **Risks**: `aria-label="Risk: [name], severity [severity]"`
- **Keyboard**: Tab through items, Enter opens detail

---

## Loading

- **Skeleton**: Score ring + 3 dimension bars + 2 risk cards
- **Delay**: 150ms

---

## Errors

- **No Assessment**: "Trust assessment not available"
- **Stale Data**: "Assessment older than 24h — refresh recommended"

---

## Keyboard

| Key | Action |
|-----|--------|
| `Tab` | Navigate dimensions/risks |
| `Enter` / `Space` | Expand item detail |
| `Escape` | Close detail |

---

## Mobile

- **< 640px**: Stacked layout, collapsible sections
- **Score**: Large circular progress at top
- **Dimensions**: Accordion list
- **Risks**: Red badges with count

---

## Permissions

| Role | View |
|------|------|
| All authenticated | ✅ |

---

## Telemetry

| Event | Properties |
|-------|------------|
| `trust_panel_view` | `variant`, `level`, `score` |
| `trust_dimension_click` | `dimension_id`, `score` |
| `trust_risk_click` | `risk_id`, `severity` |
| `trust_assurance_click` | `assurance_id`, `verified` |

---

## React Query

```typescript
const { data } = useQuery({
  queryKey: executiveKeys.report(tenderId),
  select: (report) => ({
    overallScore: report.report.win_prediction.confidence,
    level: report.report.win_prediction.confidence_level,
    // ... map to trust structure
  })
});
```

---

## Dependencies

- `TrustScoreRing` (circular progress with level)
- `DimensionBar` (horizontal bar with status)
- `RiskCard` (risk card with severity badge)
- `AssuranceBadge` (verified/unverified)
- `SeverityBadge` (color-coded)
- `ExpandableSection` (for details)
- `lucide-react`: `Shield`, `ShieldCheck`, `ShieldAlert`, `AlertTriangle`, `CheckCircle`, `XCircle`, `Info`, `Flag`, `Lock`, `Unlock`, `Eye`, `EyeOff`, `Scale`, `AlertCircle`, `ChevronRight`, `ChevronDown`

---

## Trust Level Mapping

| Score Range | Level | Color | Icon | Action |
|-------------|-------|-------|------|--------|
| 0.85 - 1.00 | High | Green | `ShieldCheck` | Proceed |
| 0.70 - 0.84 | Medium | Blue | `Shield` | Proceed with review |
| 0.50 - 0.69 | Low | Yellow | `ShieldAlert` | Additional review required |
| 0.00 - 0.49 | Critical | Red | `ShieldAlert` | Escalate/Block |

---

## Dimension Examples

| Dimension | Weight | Pass Criteria |
|-----------|--------|---------------|
| Data Quality | 0.25 | Completeness > 90%, Freshness < 7d |
| Model Confidence | 0.30 | Model score > 0.8 |
| Evidence Strength | 0.20 | ≥3 independent sources |
| Regulatory Compliance | 0.15 | All PPR checks pass |
| Historical Accuracy | 0.10 | Past predictions > 75% accurate |

---

## Risk Examples

| Risk | Severity | Likelihood | Impact | Mitigation |
|------|----------|------------|--------|------------|
| Stale market data | High | 0.7 | 0.8 | Schedule daily market refresh |
| Single source dependency | Medium | 0.4 | 0.6 | Add secondary data provider |
| Model drift | Medium | 0.3 | 0.7 | Monthly retraining schedule |
| Incomplete document extraction | Low | 0.2 | 0.4 | Manual review fallback |

---

## Layout Structure

```
┌─────────────────────────────────────────────────────────────┐
│  Trust Assessment: HIGH                    [Score: 87%]    │
│  ████████████████████░░ 87%                              │
├─────────────────────────────────────────────────────────────┤
│  DIMENSIONS                                    [Expand ▼]  │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ Data Quality          ████████████████░░  92% ✓ PASS   │   │
│  │ Model Confidence      █████████████████░  88% ✓ PASS │   │
│  │ Evidence Strength     ██████████████░░░░  75% ⚠ WARN │   │
│  │ Regulatory Compliance ██████████████████  95% ✓ PASS │   │
│  └─────────────────────────────────────────────────────┘   │
├─────────────────────────────────────────────────────────────┤
│  RISKS (2)                                        [View All]│
│  ⚠ Stale market data (High) — Mitigation: Daily refresh    │
│  ⚠ Single source dependency (Medium) — Add provider        │
├─────────────────────────────────────────────────────────────┤
│  ASSURANCES (3)                                            │
│  ✓ Data freshness verified (Automated)                     │
│  ✓ Model retrained weekly (Automated)                      │
│  ✓ Compliance audit passed (Third-party)                   │
└─────────────────────────────────────────────────────────────┘
```

---

## Future Extensions

- [ ] Trust trend over time
- [ ] Peer comparison (industry benchmarks)
- [ ] Automated remediation suggestions
- [ ] Integration with governance dashboard
- [ ] Regulatory audit export