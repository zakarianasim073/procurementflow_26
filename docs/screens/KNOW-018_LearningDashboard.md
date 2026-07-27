# KNOW-018: Learning Dashboard Screen Specification

**Module:** `features/learning-dashboard/LearningDashboardPage`
**Layer:** features
**Version:** 1.0.0
**Status:** Draft
**Workspace:** Knowledge

## Purpose
Track learning progress, training materials, and skill development.

## Screen Layout

```
┌─────────────────────────────────────────────────────────────┐
│ ExecutiveHeader                                             │
├──────────┬──────────────────────────────────────────────────┤
│          │ Breadcrumb: Knowledge > Learning Dashboard        │
│ Workspace├──────────────────────────────────────────────────┤
│   Nav    │ LearningDashboardHeader (progress, streak)       │
│          ├──────────────────────────────────────────────────┤
│          │ LearningDashboard (main content)                 │
│          │ ┌────────────────────────────────────────────┐   │
│          │ │ ProgressOverview (summary)                  │   │
│          │ ├────────────────────────────────────────────┤   │
│          │ │ Tabs: [Courses] [Progress] [Achievements]  │   │
│          │ ├────────────────────────────────────────────┤   │
│          │ │ CoursesTab (training courses)               │   │
│          │ │ ProgressTab (learning progress)             │   │
│          │ │ AchievementsTab (badges, certificates)      │   │
│          │ └────────────────────────────────────────────┘   │
├──────────┴──────────────────────────────────────────────────┤
│ AiDock (learning suggestions)                               │
└─────────────────────────────────────────────────────────────┘
```

## Component Tree

```
LearningDashboardPage
├── ExecutiveHeader
├── Breadcrumb
├── LearningDashboardHeader
│   ├── KpiStrip (courses_completed, streak, achievements)
│   └── Button (Browse Courses)
├── LearningDashboard
│   ├── ProgressOverview
│   │   ├── Chart (learning_trend)
│   │   ├── Chart (skill_distribution)
│   │   └── Chart (completion_rate)
│   ├── Tabs
│   │   ├── CoursesTab
│   │   │   └── CourseList
│   │   │       └── CourseCard × N
│   │   │           ├── title
│   │   │           ├── description
│   │   │           ├── progress
│   │   │           ├── duration
│   │   │           └── Button (Continue)
│   │   ├── ProgressTab
│   │   │   └── ProgressList
│   │   │       └── ProgressItem × N
│   │   │           ├── skill
│   │   │           ├── level
│   │   │           ├── progress
│   │   │           └── Button (Practice)
│   │   └── AchievementsTab
│   │       └── AchievementGrid
│   │           └── AchievementCard × N
│   │               ├── icon
│   │               ├── title
│   │               ├── description
│   │               └── earned_date
│   └── LearningPath
│       └── PathStep × N
│           ├── title
│           ├── status
│           └── next_step
└── AiDock
    ├── AgentCard (Learning Agent)
    └── EvidencePanel (learning suggestions)
```

## Data Sources

### Learning Data
```typescript
// API: GET /api/v1/knowledge/learning
interface LearningData {
  courses: Course[];
  progress: SkillProgress[];
  achievements: Achievement[];
  learning_path: LearningPath[];
}

interface Course {
  course_id: string;
  title: string;
  description: string;
  progress: number;
  duration: number;
  modules: number;
  completed_modules: number;
  last_accessed: string;
}

interface SkillProgress {
  skill: string;
  level: 'beginner' | 'intermediate' | 'advanced' | 'expert';
  progress: number;
  exercises_completed: number;
  last_practiced: string;
}

interface Achievement {
  achievement_id: string;
  title: string;
  description: string;
  icon: string;
  earned_date: string;
  rarity: 'common' | 'rare' | 'epic' | 'legendary';
}

interface LearningPath {
  step_id: string;
  title: string;
  status: 'completed' | 'in_progress' | 'locked';
  next_step?: string;
}
```

### React Query
```typescript
const { data: learning } = useQuery({
  queryKey: ['knowledge', 'learning'],
  queryFn: () => api.get('/api/v1/knowledge/learning'),
});

const continueCourse = useMutation({
  mutationFn: (courseId: string) => api.post(`/api/v1/knowledge/learning/courses/${courseId}/continue`),
  onSuccess: () => {
    queryClient.invalidateQueries({ queryKey: ['knowledge', 'learning'] });
    toast.success('Course resumed');
  },
});
```

## Zustand Store
```typescript
// stores/learningDashboardStore.ts
interface LearningDashboardState {
  activeTab: string;
  setTab: (tab: string) => void;
}
```

## Interactions

### Continue Course
1. Click Continue button
2. Resume course
3. Update progress
4. Track completion

### View Progress
1. Click Progress tab
2. View skills
3. Check levels
4. Practice exercises

### View Achievements
1. Click Achievements tab
2. View badges
3. Check rarity
4. Read descriptions

### Browse Courses
1. Click Browse Courses
2. View catalog
3. Select course
4. Start learning

## Responsive Breakpoints

| Breakpoint | Layout |
|------------|--------|
| Desktop (>1024px) | Full tabs + cards |
| Tablet (768-1024px) | Stacked tabs |
| Mobile (<768px) | Simplified view |

## Loading States
- Learning: Loading data
- Courses: Skeleton cards
- Progress: Loading chart

## Error States
- Load failure: Retry button
- Course failure: Error details
- Network error: Toast notification

## Accessibility
- Courses are focusable
- Progress announced via `aria-live`
- Screen reader: "Course: BOQ Analysis, 75% complete"
- Keyboard: Tab through courses

## Telemetry
- `learning_dashboard.view` — Screen loaded
- `learning_dashboard.course_continue` — Course continued
- `learning_dashboard.practice` — Skill practiced
- `learning_dashboard.achievement_earned` — Achievement earned

## Implementation Notes
- Course management
- Skill tracking
- Achievement system
- AiDock provides learning suggestions
- Progress visualization
