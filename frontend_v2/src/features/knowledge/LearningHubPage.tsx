import { BookOpen, Play, CheckCircle } from 'lucide-react'
import { Card } from '@shared/ui/Card'
import { Badge } from '@shared/ui/Badge'
import { Button } from '@shared/ui/Button'
import { Progress } from '@shared/ui/Progress'
import { Skeleton } from '@shared/ui/Skeleton'
import { ScreenTemplate } from '@layouts/index'
import { useRecentAgentRuns, useCourses } from '@hooks/index'

const COURSES = [
  {
    id: 'boq-101',
    title: 'BOQ Analysis Fundamentals',
    description: 'Learn how to read, analyze, and compare Bill of Quantities across agencies',
    duration: '2h 30m',
    modules: 8,
    completedModules: 6,
    status: 'in_progress',
  },
  {
    id: 'sor-101',
    title: 'SOR Rate Comparison',
    description: 'Master Schedule of Rates comparison across BWDB, PWD, and LGED',
    duration: '1h 45m',
    modules: 6,
    completedModules: 6,
    status: 'completed',
  },
  {
    id: 'pricing-101',
    title: 'Tender Pricing Strategy',
    description: 'Develop winning pricing strategies using discount analysis and win probability',
    duration: '3h 00m',
    modules: 10,
    completedModules: 2,
    status: 'in_progress',
  },
  {
    id: 'compliance-101',
    title: 'PPR 2025 Compliance',
    description: 'Understand Public Procurement Rules 2025 and compliance requirements',
    duration: '2h 00m',
    modules: 7,
    completedModules: 0,
    status: 'not_started',
  },
  {
    id: 'egp-101',
    title: 'e-GP Portal Navigation',
    description: 'Navigate the e-Procurement Government portal for tender discovery and submission',
    duration: '1h 30m',
    modules: 5,
    completedModules: 5,
    status: 'completed',
  },
]

function CourseCard({ course }: { course: typeof COURSES[0] }) {
  const progress = Math.round((course.completedModules / course.modules) * 100)

  return (
    <Card className="p-4">
      <div className="flex items-start justify-between">
        <div className="flex items-start gap-3">
          <div className={`rounded-lg p-2 ${
            course.status === 'completed' ? 'bg-green-100 dark:bg-green-900/30' :
            course.status === 'in_progress' ? 'bg-blue-100 dark:bg-blue-900/30' :
            'bg-gray-100 dark:bg-gray-800'
          }`}>
            {course.status === 'completed' ? (
              <CheckCircle className="h-5 w-5 text-green-600 dark:text-green-400" />
            ) : course.status === 'in_progress' ? (
              <Play className="h-5 w-5 text-blue-600 dark:text-blue-400" />
            ) : (
              <BookOpen className="h-5 w-5 text-gray-500" />
            )}
          </div>
          <div>
            <h3 className="text-sm font-semibold text-gray-900 dark:text-white">{course.title}</h3>
            <p className="mt-1 text-xs text-gray-500 dark:text-gray-400">{course.description}</p>
          </div>
        </div>
        <Badge tone={course.status === 'completed' ? 'success' : course.status === 'in_progress' ? 'info' : 'default'}>
          {course.status === 'completed' ? 'Completed' : course.status === 'in_progress' ? 'In Progress' : 'Not Started'}
        </Badge>
      </div>

      <div className="mt-4">
        <div className="flex items-center justify-between text-xs text-gray-500 dark:text-gray-400">
          <span>{course.completedModules}/{course.modules} modules</span>
          <span>{course.duration}</span>
        </div>
        <Progress value={progress} className="mt-2" />
      </div>

      <Button variant="secondary" className="mt-3 w-full">
        {course.status === 'completed' ? 'Review' : course.status === 'in_progress' ? 'Continue' : 'Start Course'}
      </Button>
    </Card>
  )
}

export function LearningHubPage() {
  const { data: coursesData, isLoading } = useCourses()
  const { data: runsRes } = useRecentAgentRuns(10)

  const courses = coursesData
    ? coursesData.map((course) => ({ ...course, completedModules: course.completed_modules }))
    : COURSES

  const completedCount = courses.filter(c => c.status === 'completed').length
  const inProgressCount = courses.filter(c => c.status === 'in_progress').length

  if (isLoading) {
    return (
      <ScreenTemplate
        header={
          <div>
            <h1 className="text-lg font-semibold text-gray-900 dark:text-white">Learning Hub</h1>
            <p className="text-sm text-gray-500 dark:text-gray-400">Training courses and tutorials for procurement workflows</p>
          </div>
        }
        primary={<div className="space-y-4">{Array.from({ length: 3 }).map((_, i) => <Skeleton key={i} className="h-32 w-full rounded-xl" />)}</div>}
      />
    )
  }

  return (
    <ScreenTemplate
      header={
        <div>
          <h1 className="text-lg font-semibold text-gray-900 dark:text-white">Learning Hub</h1>
          <p className="text-sm text-gray-500 dark:text-gray-400">Training courses and tutorials for procurement workflows</p>
        </div>
      }
      kpiStrip={
        <>
          <div className="rounded-xl border border-gray-200 bg-white px-4 py-3 dark:border-gray-700 dark:bg-gray-800">
            <span className="text-xs text-gray-500 dark:text-gray-400">Courses</span>
            <p className="text-lg font-bold text-gray-900 dark:text-white">{courses.length}</p>
          </div>
          <div className="rounded-xl border border-gray-200 bg-white px-4 py-3 dark:border-gray-700 dark:bg-gray-800">
            <span className="text-xs text-gray-500 dark:text-gray-400">Completed</span>
            <p className="text-lg font-bold text-green-600 dark:text-green-400">{completedCount}</p>
          </div>
          <div className="rounded-xl border border-gray-200 bg-white px-4 py-3 dark:border-gray-700 dark:bg-gray-800">
            <span className="text-xs text-gray-500 dark:text-gray-400">In Progress</span>
            <p className="text-lg font-bold text-blue-600 dark:text-blue-400">{inProgressCount}</p>
          </div>
        </>
      }
      primary={
        <div className="space-y-4">
          {inProgressCount > 0 && (
            <div>
              <h2 className="mb-3 text-sm font-semibold text-gray-700 dark:text-gray-300">Continue Learning</h2>
              <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
                {courses.filter(c => c.status === 'in_progress').map(course => (
                  <CourseCard key={course.id} course={course} />
                ))}
              </div>
            </div>
          )}

          <div>
            <h2 className="mb-3 text-sm font-semibold text-gray-700 dark:text-gray-300">All Courses</h2>
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
              {courses.filter(c => c.status !== 'in_progress').map(course => (
                <CourseCard key={course.id} course={course} />
              ))}
            </div>
          </div>
        </div>
      }
    />
  )
}
