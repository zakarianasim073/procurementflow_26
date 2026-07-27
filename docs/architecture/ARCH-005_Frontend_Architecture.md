# ARCH-005: Frontend Component Architecture

```mermaid
graph TB
    subgraph "app/"
        ROOT[App.tsx<br/>Routes + Providers]
        SHELL[AppShell<br/>Layout + Nav]
    end

    subgraph "features/"
        subgraph "Executive"
            EX_DASH[ExecutivePage]
            EX_PIPE[PipelinePage]
        end
        subgraph "Tender"
            TE_LIST[TenderListPage]
            TE_DETAIL[TenderDetailPage]
            TE_WS[TenderWorkspacePage]
            TE_BOQ[BoqPage]
            TE_COMP[CompliancePage]
            TE_CPT[CompetitorsPage]
            TE_SUB[SubmissionPage]
            TE_AWD[AwardPage]
            TE_PRICE[PricingLaboratory]
        end
        subgraph "Opportunity"
            OP_DISC[DiscoveryPage]
            OP_QUAL[QualificationPage]
            OP_MON[MonitoringPage]
        end
        subgraph "Trust"
            TR_CHAT[TrustChatPage]
            TR_AGENT[TrustAgentsPage]
            TR_RES[AgentResultPage]
        end
        subgraph "Knowledge"
            KN_MKT[KnowledgePage]
            KN_SOR[SorPage]
            KN_ANAL[AnalyticsPage]
            KN_DOC[DocumentToolsPage]
            KNLearn[LearningHubPage]
            KN_SRCH[KnowledgeSearchPage]
            KN_BRAIN[CompanyBrainPage]
            KN_CLAUSE[ClauseExplorer]
        end
    end

    subgraph "widgets/"
        WD_TENDER[TenderCard]
        WD_BOQ[BOQTable]
        WD_AGENT[AgentStatusCard]
    end

    subgraph "features/ui/"
        UI_BTN[Button]
        UI_CARD[Card]
        UI_BADGE[Badge]
        UI_INPUT[Input]
        UI_TABS[Tabs]
        UI_TABLE[DataTable]
        UI_CHART[Chart]
        UI_SKELETON[Skeleton]
        UI_EMPTY[EmptyState]
        UI_MODAL[Modal]
    end

    subgraph "entities/"
        EN_TENDER[tender API]
        EN_BOQ[boq API]
        EN_SOR[sor API]
        EN_CONTR[contractor API]
        EN_COMP[competitor API]
        EN_SUB[submission API]
        EN_AWARD[award API]
    end

    subgraph "shared/"
        SH_API[fetchJson]
        SH_NAV[navigation]
        SH_ROUTING[useNavigate + useParams]
    end

    subgraph "providers/"
        PR_QUERY[React Query Provider]
        PR_ZUSTAND[Zustand Store]
    end

    ROOT --> SHELL
    SHELL --> TE_LIST
    SHELL --> KN_MKT
    SHELL --> TR_CHAT
    TE_WS --> TE_BOQ
    TE_WS --> TE_COMP
    TE_WS --> TE_CPT
    TE_WS --> TE_SUB
    TE_WS --> TE_AWD
    TE_BOQ --> EN_BOQ
    KN_SOR --> EN_SOR
    EN_BOQ --> SH_API
    EN_SOR --> SH_API
```

## Feature-Sliced Design Layers

| Layer | Purpose | Examples |
|-------|---------|---------|
| `app/` | Entry point, providers, routing | App.tsx, QueryClient setup |
| `features/` | User-facing pages | TenderListPage, SorPage |
| `entities/` | Domain data (types + API) | boq/, sor/, competitor/ |
| `widgets/` | Composed UI blocks | TenderCard, BOQTable |
| `shared/` | Reusable UI primitives | Button, Card, Badge |
| `layouts/` | Page layouts | ScreenTemplate, AppShell |
| `providers/` | Context providers | React Query, Zustand |
| `hooks/` | Data hooks | useTenderList, useSorSearch |
