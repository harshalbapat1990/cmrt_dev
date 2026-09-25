import { useUser } from '../../context/UserContext';

const ROLE_LABELS: Record<string, string> = {
  SUPER_ADMIN: 'Super Admin',
  ORG_ADMIN: 'Organisation Admin',
  PROJECT_ADMIN: 'Project Admin',
  PROJECT_EDITOR: 'Project Editor',
  PROJECT_VIEWER: 'Project Viewer',
};

const ROLE_COLOURS: Record<string, string> = {
  SUPER_ADMIN: 'bg-red-100 text-red-800',
  ORG_ADMIN: 'bg-purple-100 text-purple-800',
  PROJECT_ADMIN: 'bg-blue-100 text-blue-800',
  PROJECT_EDITOR: 'bg-emerald-100 text-emerald-800',
  PROJECT_VIEWER: 'bg-slate-100 text-slate-700',
};

function Field({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div className="flex flex-col gap-1">
      <dt className="text-xs font-medium uppercase tracking-wide text-slate-500">{label}</dt>
      <dd className="text-sm text-slate-800 break-all">{value ?? <span className="text-slate-400 italic">—</span>}</dd>
    </div>
  );
}

export default function UserProfile() {
  const { user, roles } = useUser();

  if (!user) {
    return (
      <div className="flex min-h-screen items-center justify-center text-slate-400">
        Not logged in.
      </div>
    );
  }

  const displayName =
    [user.first_name, user.last_name].filter(Boolean).join(' ') || null;

  return (
    <div className="min-h-screen bg-neutral-50">
      <div className="mx-auto mt-12 max-w-2xl px-4">
        <h2 className="mb-8 text-3xl font-light text-slate-700">User Profile</h2>

        <div className="overflow-hidden rounded-[var(--radius-3)] border border-slate-200 bg-white shadow-sm">
          <div className="flex items-center gap-5 border-b border-slate-100 bg-[#F7F7F7] px-8 py-6">
            <div className="flex h-14 w-14 shrink-0 items-center justify-center rounded-full bg-slate-300 text-xl font-semibold text-slate-700 ring-2 ring-white">
              {displayName
                ? displayName
                    .split(' ')
                    .map((n) => n[0])
                    .join('')
                    .toUpperCase()
                    .slice(0, 2)
                : user.email.slice(0, 2).toUpperCase()}
            </div>
            <div>
              <p className="text-lg font-medium text-slate-800">
                {displayName ?? user.email}
              </p>
              <p className="text-sm text-slate-500">{user.email}</p>
            </div>
          </div>

          <dl className="grid grid-cols-1 gap-6 px-8 py-7 sm:grid-cols-2">
            <Field label="First name" value={user.first_name} />
            <Field label="Last name" value={user.last_name} />
            <Field label="Email" value={user.email} />
            <Field label="Organisation" value={user.organisation_name} />
          </dl>

          <div className="border-t border-slate-100 px-8 py-6">
            <p className="mb-3 text-xs font-medium uppercase tracking-wide text-slate-500">
              Assigned roles
            </p>
            {roles.length === 0 ? (
              <p className="text-sm italic text-slate-400">No roles assigned</p>
            ) : (
              <div className="flex flex-wrap gap-2">
                {roles.map((r) => (
                  <span
                    key={r}
                    className={`inline-flex items-center rounded-full px-3 py-1 text-xs font-medium ${
                      ROLE_COLOURS[r] ?? 'bg-slate-100 text-slate-700'
                    }`}
                  >
                    {ROLE_LABELS[r] ?? r}
                  </span>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
