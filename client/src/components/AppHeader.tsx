import { NavLink } from "react-router-dom";
import { useRef, useState, useEffect } from "react";
import { useUser } from "../context/UserContext";

type AppHeaderProps = {
  projectName: string;
  isSaved: boolean;
  projectId: string;
  onNavigateOverview?: () => void;
  onNavigateDatasets?: () => void;
};

function getInitials(email: string): string {
  const username = email.split("@")[0];
  const parts = username.split(/[._-]/).filter(Boolean);
  if (parts.length >= 2) return (parts[0][0] + parts[1][0]).toUpperCase();
  return username.slice(0, 2).toUpperCase();
}

const AppHeader: React.FC<AppHeaderProps> = ({
  projectName,
  isSaved,
  // projectId,
  onNavigateOverview,
  onNavigateDatasets,
}) => {
  const { user, logout } = useUser();
  const initials = user ? getInitials(user.email) : "";
  const [dropdownOpen, setDropdownOpen] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!dropdownOpen) return;
    const handler = (e: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(e.target as Node)) {
        setDropdownOpen(false);
      }
    };
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, [dropdownOpen]);

  return (
    <header className="shrink-0 border-b border-neutral-90 bg-white shadow-sm z-30">
      <div className="flex flex-row h-[var(--header-height)] px-6 justify-between items-center">
        <div className="flex items-center gap-3 min-w-0">
          <span className="font-bold text-base text-project-name whitespace-nowrap">
            Carbon Measurement &amp; Reporting Tool
          </span>
          {projectName && (
            <>
              <span className="text-neutral-300 select-none">|</span>
              <span className="font-bold text-base text-text-dark truncate max-w-xs">
                {projectName}
              </span>
            </>
          )}
          {isSaved && (
            <span className="flex items-center gap-1 ml-2 px-2.5 py-0.5 rounded-full text-xs font-medium bg-green-50 text-green-700 border border-green-200 whitespace-nowrap">
              <svg className="w-3.5 h-3.5" viewBox="0 0 20 20" fill="currentColor" aria-hidden="true">
                <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
              </svg>
              Saved
            </span>
          )}
        </div>

        <div className="flex items-center gap-2">
          <nav className="hidden md:flex items-center gap-8">
            <button
              onClick={onNavigateOverview}
              className="relative px-1 pt-2 pb-2 text-text-base hover:text-primary transition-colors text-sm"
            >
              Overview
            </button>

            <button
              onClick={onNavigateDatasets}
              className="relative px-1 pt-2 pb-2 text-text-base hover:text-primary transition-colors text-sm"
            >
              Datasets
            </button>

            <NavLink
              to="/user-guide"
              className={({ isActive }) =>
                `relative px-1 pb-2 pt-2 transition-colors text-sm ${
                  isActive ? "text-primary font-medium" : "text-text-base hover:text-primary"
                }`
              }
            >
              {({ isActive }) => (
                <>
                  User Guide
                  {isActive && (
                    <span className="absolute left-0 -bottom-[12px] w-full h-[2px] bg-primary" />
                  )}
                </>
              )}
            </NavLink>
          </nav>

          {user && (
            <div className="relative ml-6" ref={dropdownRef}>
              <button
                aria-label={`${user.email} — open menu`}
                aria-expanded={dropdownOpen}
                onClick={() => setDropdownOpen((o) => !o)}
                title={`Logged in as ${user.email}`}
                className="inline-flex h-8 w-8 items-center justify-center rounded-full bg-slate-200 text-slate-700 font-semibold ring-1 ring-inset ring-slate-300 hover:bg-slate-300 focus-visible:ring-2 focus-visible:ring-blue-600/30 transition-colors text-sm cursor-pointer"
              >
                {initials}
              </button>

              {dropdownOpen && (
                <div className="absolute right-0 mt-2 w-48 rounded-lg border border-neutral-200 bg-white shadow-lg z-50 py-1">
                  <NavLink
                    to="/profile"
                    onClick={() => setDropdownOpen(false)}
                    className="flex items-center gap-2 cursor-pointer w-full px-4 py-2 text-sm text-text-base hover:bg-neutral-50 transition-colors"
                  >
                    Profile
                  </NavLink>
                  <button
                    onClick={() => { logout(); setDropdownOpen(false); }}
                    className="flex items-center gap-2 w-full cursor-pointer px-4 py-2 text-sm text-text-base hover:bg-neutral-50 transition-colors"
                  >
                    Sign out
                  </button>
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </header>
  );
};

export default AppHeader;
