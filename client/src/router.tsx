import { lazy, Suspense } from 'react'
import {
  createBrowserRouter,
} from 'react-router-dom'
import { App } from './App'
import RouteErrorBoundary from './routeErrorBoundary'


// Page chunks loaded on demand — each route gets its own JS chunk
const MonthlyReport    = lazy(() => import('./pages/monthlyReport/MonthlyReport'))
const AddNewProject    = lazy(() => import('./pages/addNewProject/AddNewProject'))
const HomePage         = lazy(() => import('./pages/home/Homepage'))
const ManageUserAccess = lazy(() => import('./pages/ManageAccess/ManageUserAccess'))
const UserProfile      = lazy(() => import('./pages/profile/UserProfile'))
const DummyTable       = lazy(() => import('./pages/dummy-table/DummyTable'))
const BusinessCaseStage = lazy(() => import('./pages/smallProject/dataEntry/DataEntry'))
const ProjectDetail    = lazy(() => import('./pages/project/ProjectDetail'))
const DatasetsPage        = lazy(() => import('./pages/datasets/DatasetsPage'))
const OrgDatasetsPage     = lazy(() => import('./pages/datasets/OrgDatasetsPage'))
const ProjectDatasetsSelectPage = lazy(() => import('./pages/datasets/ProjectDatasetsSelectPage'))
const ProjectDatasetsPage = lazy(() => import('./pages/datasets/ProjectDatasetsPage'))
const ResultDashboard = lazy(() => import('./pages/resultDashboard/ResultDashboard'))
const ViewCalculations = lazy(() => import('./pages/resultDashboard/ViewCalculations'))
const OrgResultDashboard = lazy(() => import('./pages/resultDashboard/OrgResultDashboard'))
const AuditLogPage    = lazy(() => import('./pages/auditLog/AuditLogPage'))
const StageResubmissionAuditPage = lazy(() => import('./pages/auditLog/StageResubmissionAuditPage'))
const UserGuidePage   = lazy(() => import('./pages/userGuide/UserGuidePage'))
const TermsAndConditionsAdminPage = lazy(() => import('./pages/termsAndConditions/TermsAndConditionsAdminPage'))
const LandingPage     = lazy(() => import('./pages/landingPage/LandingPage'))

function Loading() {
  return <div className="flex items-center justify-center h-full text-slate-400">Loading…</div>
}

export const router = createBrowserRouter([
  {
    path: '/',
    element: <App />,
    errorElement: <RouteErrorBoundary />,
    children: [
       {index: true, element: <Suspense fallback={<Loading />}><LandingPage /></Suspense> },
      { index: true, path: 'AddNewProject/', element: <Suspense fallback={<Loading />}><AddNewProject mode="create" /></Suspense> },
      { index: true, path: '/projects/:projectId/edit', element: <Suspense fallback={<Loading />}><AddNewProject mode="edit" /></Suspense> },      
      { path: 'MonthlyReport/', element: <Suspense fallback={<Loading />}><MonthlyReport /></Suspense> },
      {path: 'DummyPage/', element: <Suspense fallback={<Loading />}><DummyTable /></Suspense> },
      { path: 'Home/admin',  element: <Suspense fallback={<Loading />}><HomePage /></Suspense> },
      { path: 'Home/user',   element: <Suspense fallback={<Loading />}><HomePage /></Suspense> },
      { path: 'Home/',       element: <Suspense fallback={<Loading />}><HomePage /></Suspense> },
      { path: 'ManageUserAccess/admin',      element: <Suspense fallback={<Loading />}><ManageUserAccess role="admin" /></Suspense> },
      { path: 'ManageUserAccess/orgadmin',   element: <Suspense fallback={<Loading />}><ManageUserAccess role="orgadmin" /></Suspense> },
      { path: 'ManageUserAccess/superadmin', element: <Suspense fallback={<Loading />}><ManageUserAccess role="superadmin" /></Suspense> },
      { path: 'profile',     element: <Suspense fallback={<Loading />}><UserProfile /></Suspense> },
      { path: 'dataEntry', element: <Suspense fallback={<Loading />}><BusinessCaseStage /></Suspense>},
      { path: 'projects/:projectId', element: <Suspense fallback={<Loading />}><ProjectDetail /></Suspense> },
      { path: 'projects/:projectId/audit', element: <Suspense fallback={<Loading />}><AuditLogPage /></Suspense> },
      { path: 'projects/:projectId/audit/stage/:stageInstanceId', element: <Suspense fallback={<Loading />}><StageResubmissionAuditPage /></Suspense> },
      { path: 'user-guide', element: <Suspense fallback={<Loading />}><UserGuidePage /></Suspense> },
      { path: 'admin/terms-and-conditions', element: <Suspense fallback={<Loading />}><TermsAndConditionsAdminPage /></Suspense> },
      { path: 'datasets',                   element: <Suspense fallback={<Loading />}><DatasetsPage /></Suspense> },
      { path: 'datasets/org',               element: <Suspense fallback={<Loading />}><OrgDatasetsPage /></Suspense> },
      { path: 'datasets/project',           element: <Suspense fallback={<Loading />}><ProjectDatasetsSelectPage /></Suspense> },
      { path: 'datasets/project/:projectId', element: <Suspense fallback={<Loading />}><ProjectDatasetsPage /></Suspense> },
      { path: 'resultsDashboard/',element :<Suspense fallback={<Loading />}><ResultDashboard /></Suspense>},
      { path: 'OrgResultDashboard/', element: <Suspense fallback={<Loading />}><OrgResultDashboard /></Suspense>},
      { path: 'resultsDashboard/detailedCalculations/', element: <Suspense fallback={<Loading />}><ViewCalculations /></Suspense>},
      { path: '*', element: <div className="text-slate-300">Not Found</div> },
    ],
  },
])
