
import { Outlet, useLocation, useNavigate } from 'react-router-dom'
import { useEffect } from 'react';
import Header from './components/Header'
import { UserProvider, useUser } from './context/UserContext';
import { ProjectHeaderProvider } from './context/ProjectHeaderContext';
import RegisterForm from './pages/onboarding/RegisterForm';

import LandingPageHeader from "./components/LandingPageHeader";


function AppShell() {
  const { user, roles, isLoaded, needsRegistration } = useUser();

const location = useLocation();
const navigate = useNavigate();

const isLandingPage = location.pathname === "/";

  useEffect(() => {
    // Send an already-authenticated user straight to their dashboard when Easy Auth's
    // post-login redirect lands them on the public landing page.
    if (!isLandingPage || !isLoaded || !user) return;
    navigate(roles.includes('SUPER_ADMIN') ? '/ManageUserAccess/superadmin' : '/Home/user', { replace: true });
  }, [isLandingPage, isLoaded, user, roles, navigate]);

  // Azure Easy Auth already authenticated this caller — block everything until
  // they complete app-level onboarding (registration is authorization, not auth).
  if (isLoaded && needsRegistration) {
    return <RegisterForm />;
  }

  return (
    <div className="min-h-screen bg-bg-content">
{isLandingPage ? (
   <> <LandingPageHeader />
    <main><Outlet /></main>
  </> ) : (
    <><Header />
    <main className="h-[calc(100vh-var(--header-height))] overflow-y-auto">
        <Outlet />
      </main>
      </>
  )}
    </div>
  )
}

export function App() {
  return (
    <UserProvider>
      <ProjectHeaderProvider>
        <AppShell />
      </ProjectHeaderProvider>
    </UserProvider>
  )
}
export default App;
