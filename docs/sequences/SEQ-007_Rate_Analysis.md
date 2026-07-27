# SEQ-007: Rate Analysis with Market Comparison

```mermaid
sequenceDiagram
    autonumber
    actor User as Frontend User
    participant API as POST /api/rate-analysis/from-compare
    participant CMP as BOQProcessor
    participant RAE as RateAnalysisEngine
    participant TPL as RateAnalysisTemplates
    participant MKT as MarketIndex
    participant SOR as SOR Service
    participant XL as BOQExcelGenerator
    participant DB as PostgreSQL

    User->>API: POST /api/rate-analysis/from-compare { comparison_id }
    API->>DB: Fetch BOQComparison + BOQItems
    DB-->>API: Items with SOR codes

    rect rgb(240, 248, 255)
        Note over API,RAE: Phase 1: Item-Level Analysis
        loop For each BOQ item with SOR code
            API->>RAE: analyze_boq_item(item, sor_rate)
            RAE->>TPL: get_composition(sor_code)
            TPL-->>RAE: { material: [...], labor: [...], equipment: [...] }

            loop For each sub-element
                RAE->>SOR: find_rate(sub_code)
                SOR-->>RAE: composite_rate
                RAE->>MKT: get_market_price(material_name)
                MKT-->>RAE: market_price
            end
            RAE->>RAE: total_cost = sum(material + labor + equipment)
            RAE->>RAE: profit_margin = (sor_rate - total_cost) / total_cost × 100
            RAE-->>API: { item_code, sor_rate, cost_breakdown, margin_pct }
        end
    end

    rect rgb(240, 255, 240)
        Note over API,XL: Phase 2: Report Generation
        API->>XL: generate_rate_analysis_excel(items, cost_breakdowns)
        XL->>XL: Tab 1: Summary (item, SOR, market, margin)
        XL->>XL: Tab 2: Material Breakdown
        XL->>XL: Tab 3: Labor Breakdown
        XL->>XL: Tab 4: Equipment Breakdown
        XL->>XL: Tab 5: Market Price Comparison
        XL->>XL: Tab 6: Profit Margin Analysis
        XL-->>API: Excel file path
    end

    API-->>User: { analysis_id, items_analyzed, avg_margin, excel_url }
```

## Cost Breakdown Structure

```
SOR Rate (100%)
├── Material Cost (typically 55-65%)
│   ├── Cement
│   ├── Steel
│   ├── Sand/Aggregate
│   ├── Bricks
│   └── Other materials
├── Labor Cost (typically 20-30%)
│   ├── Mason
│   ├── Carpenter
│   ├── Rod Bender
│   ├── Helper
│   └── Other labor
└── Equipment Cost (typically 10-15%)
    ├── Excavator
    ├── Dozer
    ├── Mixer
    └── Other equipment
```

## Market Index Sources

| Material | Source | Update Frequency |
|----------|--------|-----------------|
| Cement | BD market rates | Weekly |
| Steel | Import + local | Monthly |
| Sand | Local suppliers | Monthly |
| Aggregate | Quarry rates | Monthly |
| Bricks | Factory prices | Monthly |
