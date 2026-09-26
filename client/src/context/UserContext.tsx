import {
  createContext,
  useContext,
  useEffect,
  useState,
  useCallback,
  type ReactNode,
} from 'react';
import http from '@/http';

export type MeProfile = {
  user_id: string;
  email: string;
  organisation_id: string | null;
  organisation_name: string | null;
  first_name: string | null;
  last_name: string | null;
  username: string | null;
};

type UserState = {
  user: MeProfile | null;
  roles: string[];
  isLoaded: boolean;
  needsRegistration: boolean;
  pendingEmail: string | null;
};

type UserContextValue = UserState & {
  refreshUser: () => Promise<void>;
  logout: () => void;
};

const UserContext = createContext<UserContextValue | null>(null);

const initialState: UserState = {
  user: null,
  roles: [],
  isLoaded: false,
  needsRegistration: false,
  pendingEmail: null,
};

export function UserProvider({ children }: { children: ReactNode }) {
  const [state, setState] = useState<UserState>(initialState);

  const refreshUser = useCallback(async () => {
    let profile: MeProfile;
    try {
      const meRes = await http.get('/api/me');
      profile = meRes.data;
    } catch {
      // /api/me requires a CMRT account. A valid Easy Auth identity without a
      // matching database user should be routed into app registration.
      try {
        const ctxRes = await http.get('/api/identity/registration-context');
        setState({
          user: null,
          roles: [],
          isLoaded: true,
          needsRegistration: Boolean(ctxRes.data?.needs_registration),
          pendingEmail: ctxRes.data?.email ?? null,
        });
      } catch {
        setState({ user: null, roles: [], isLoaded: true, needsRegistration: false, pendingEmail: null });
      }
      return;
    }

    try {
      const accessRes = await http.get('/api/me/access');
      setState({
        user: profile,
        roles: accessRes.data.effective_roles ?? [],
        isLoaded: true,
        needsRegistration: false,
        pendingEmail: null,
      });
    } catch {
      // A role lookup failure must not turn an authenticated, registered user
      // into an apparent logged-out user.
      setState({ user: profile, roles: [], isLoaded: true, needsRegistration: false, pendingEmail: null });
    }
  }, []);

  useEffect(() => {
    refreshUser();
  }, [refreshUser]);

  const logout = useCallback(async () => {
    // Clear Azure Easy Auth's session cookie without letting the browser follow
    // its broken federated-logout redirect to Auth0's /oidc/logout endpoint.
    try {
      await fetch('/.auth/logout', { credentials: 'include', mode: 'no-cors' });
    } catch {
      // best-effort
    }
    window.location.href = '/logout/idp';
  }, []);

  return (
    <UserContext.Provider value={{ ...state, refreshUser, logout }}>
      {children}
    </UserContext.Provider>
  );
}

export function useUser(): UserContextValue {
  const ctx = useContext(UserContext);
  if (!ctx) throw new Error('useUser must be used inside <UserProvider>');
  return ctx;
}
