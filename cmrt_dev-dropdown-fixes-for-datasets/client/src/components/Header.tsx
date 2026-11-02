import { NavLink } from "react-router-dom";
import { useRef, useState, useEffect } from "react";
import Breadcrumbs from "./common/Breadcrumbs";
import { useUser } from "../context/UserContext";
import { useProjectHeader } from "../context/ProjectHeaderContext";


function getInitials(email: string): string {
  const username = email.split('@')[0];
  const parts = username.split(/[._-]/).filter(Boolean);
  if (parts.length >= 2) return (parts[0][0] + parts[1][0]).toUpperCase();
  return username.slice(0, 2).toUpperCase();
}

const Header = () => {
  const { user, roles } = useUser();
  const { projectName: _projectName, isSaved } = useProjectHeader();
  const initials = user ? getInitials(user.email) : '';
  const [dropdownOpen, setDropdownOpen] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);

  const manageAccessPath = roles.includes('SUPER_ADMIN')
    ? '/ManageUserAccess/superadmin'
    : roles.includes('ORG_ADMIN')
    ? '/ManageUserAccess/orgadmin'
    : roles.includes('PROJECT_ADMIN')
    ? '/ManageUserAccess/admin'
    : null; // regular users don't see this option

  const datasetsPath = roles.includes('SUPER_ADMIN')
    ? '/datasets'
    : roles.includes('ORG_ADMIN')
    ? '/datasets/org'
    : (roles.includes('PROJECT_ADMIN') || roles.includes('PROJECT_EDITOR'))
    ? '/datasets/project'
    : '/datasets';

  useEffect(() => {
    if (!dropdownOpen) return;
    const handler = (e: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(e.target as Node)) {
        setDropdownOpen(false);
      }
    };
    document.addEventListener('mousedown', handler);
    return () => document.removeEventListener('mousedown', handler);
  }, [dropdownOpen]);
  return (
    <header className="sticky top-0 z-30 left-0 border-b border-neutral-90 bg-white ">
      <div className="flex flex-row h-[var(--header-height)] px-6 justify-between items-center">
        <div className="flex items-center gap-3 min-w-0">
          <div className="font-bold text-base truncate text-project-name whitespace-nowrap">
            Carbon Measurement &amp; Reporting Tool
          </div>
          <div className="ml-2">
            <Breadcrumbs />
          </div>
          {isSaved && (
            <span className="flex items-center gap-1 ml-1 px-2.5 py-0.5 rounded-full text-xs font-medium bg-green-50 text-green-700 border border-green-200 whitespace-nowrap">
              <svg className="w-3.5 h-3.5" viewBox="0 0 20 20" fill="currentColor" aria-hidden="true">
                <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
              </svg>
              Saved
            </span>
          )}
        </div>
        <div className="flex items-center gap-2">
          <nav className="hidden md:flex items-center gap-8">
          <NavLink
            to="/home"
            className={({ isActive }) =>
              `relative px-1 pt-2 pb-2 text-primary transition-colors ${
                isActive ? "text-primary font-medium" : "text-text-base"
              }`
            }
          >
          {({ isActive }) => (
            <>
              Overview
              {isActive && (
                <span className="absolute left-0 -bottom-[12px] w-19 h-[2px] bg-primary" />
              )}
            </>
          )}
        </NavLink>

        <NavLink
          to={datasetsPath}
          end
          className={({ isActive }) =>
            `relative px-1 pb-2 pt-2 text-primary transition-colors ${
              isActive ? "text-primary font-medium" : "text-text-base"
            }`
          }
        >
          {({ isActive }) => (
            <>
              Datasets
              {isActive && (
                <span className="absolute left-0 -bottom-[12px] w-19 h-[2px] bg-primary" />
              )}
            </>
          )}
        </NavLink>

        {/* {roles.includes('ORG_ADMIN') && (
          <NavLink
            to="./OrgResultDashboard"
            end
            className={({ isActive }) =>
              `relative px-1 pb-2 pt-2 text-primary transition-colors ${
                isActive ? "text-primary font-medium" : "text-text-base"
            }`
          }
        >
          {({ isActive }) => (
            <>
              Results Dashboard
              {isActive && (
                <span className="absolute left-0 -bottom-[12px] w-19 h-[2px] bg-primary" />
              )}
            </>
          )}
        </NavLink>)} */}



        <NavLink
          to="/user-guide"
          className={({ isActive }) =>
            `relative px-1 pb-2 pt-2 text-primary transition-colors ${
              isActive ? "text-primary font-medium" : "text-text-base"
            }`
          }
        >
          {({ isActive }) => (
            <>
              User Guide
              {isActive && (
                <span className="absolute left-0 -bottom-[12px] w-19 h-[2px] bg-primary" />
              )}
            </>
          )}
        </NavLink>
        {roles.includes('SUPER_ADMIN') && (
        <NavLink
          to="/admin/terms-and-conditions"
          className={({ isActive }) =>
            `relative px-1 pb-2 pt-2 text-primary transition-colors ${
              isActive ? "text-primary font-medium" : "text-text-base"
            }`
          }
        >
          {({ isActive }) => (
            <>
              Terms &amp; Conditions
              {isActive && (
                <span className="absolute left-0 -bottom-[12px] w-30 h-[2px] bg-primary" />
              )}
            </>
          )}
        </NavLink>
        )}
         {manageAccessPath && (
         <NavLink
          to={manageAccessPath}
          className={({ isActive }) =>
            `relative px-1 pb-2 pt-2 text-primary transition-colors ${
              isActive ? "text-primary font-medium" : "text-text-base"
            }`
          }
        >
          {({ isActive }) => (
            <>
              Manage User Access
              {isActive && (
                <span className="absolute left-0 -bottom-[12px] w-41 h-[2px] bg-primary" />
              )}
            </>
          )}
        </NavLink>
         )}

          </nav>
          {user && (
          <div className="relative ml-10" ref={dropdownRef}>
            <button
              aria-label={`${user.email} — open menu`}
              aria-expanded={dropdownOpen}
              onClick={() => setDropdownOpen((o) => !o)}
              title={`Logged in as ${user.email}`}
              className="inline-flex h-8 w-8 items-center justify-center rounded-full bg-slate-200 text-slate-700 font-semibold ring-1 ring-inset ring-slate-300 hover:bg-slate-300 focus-visible:ring-2 focus-visible:ring-blue-600/30 transition-colors cursor-pointer">
              {initials}
            </button>

            {user && dropdownOpen && (
              <div className="absolute right-0 mt-2 w-56 rounded-lg border border-neutral-200 bg-white shadow-lg z-50 py-1">

                <NavLink
                  to="/profile"
                  onClick={() => setDropdownOpen(false)}
                  className="flex items-center gap-2 w-full px-4 py-2 text-sm text-text-base hover:bg-neutral-50 transition-colors"
                >
                  <svg xmlns="http://www.w3.org/2000/svg" className="h-4 w-4 text-text-muted" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                    <path strokeLinecap="round" strokeLinejoin="round" d="M15.75 6a3.75 3.75 0 1 1-7.5 0 3.75 3.75 0 0 1 7.5 0ZM4.501 20.118a7.5 7.5 0 0 1 14.998 0A17.933 17.933 0 0 1 12 21.75c-2.676 0-5.216-.584-7.499-1.632Z" />
                  </svg>
                  User Profile
                </NavLink>

                {/* <div className="border-t border-neutral-100 mt-1 pt-1">
                  <button
                    onClick={() => { setDropdownOpen(false); logout(); }}
                    className="flex items-center gap-2 w-full px-4 py-2 text-sm text-red-600 hover:bg-red-50 transition-colors"
                  >
                    <svg xmlns="http://www.w3.org/2000/svg" className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                      <path strokeLinecap="round" strokeLinejoin="round" d="M15.75 9V5.25A2.25 2.25 0 0 0 13.5 3h-6a2.25 2.25 0 0 0-2.25 2.25v13.5A2.25 2.25 0 0 0 7.5 21h6a2.25 2.25 0 0 0 2.25-2.25V15m3 0 3-3m0 0-3-3m3 3H9" />
                    </svg>
                    Log Out
                  </button>
                </div> */}
              </div>
            )}
          </div>
          )}
        </div>
      </div>
    </header>
  );
};

export default Header;
