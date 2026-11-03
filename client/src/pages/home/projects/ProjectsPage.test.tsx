import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import ProjectsPage from './ProjectsPage';
import http from '@/http';
import accessRequestsService from '@/services/accessRequests.service';

const navigateMock = vi.fn();

vi.mock('react-router-dom', () => ({
  useNavigate: () => navigateMock,
}));

vi.mock('@/context/UserContext', () => ({
  useUser: () => ({ user: null }),
}));

vi.mock('@/http', () => ({ default: { get: vi.fn() } }));

vi.mock('@/services/accessRequests.service', () => ({
  default: { fetchPending: vi.fn() },
}));

describe('ProjectsPage admin pending indicators', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(http.get).mockResolvedValue({ data: [] });
    vi.mocked(accessRequestsService.fetchPending).mockResolvedValue([
      {
        id: 'request-1',
        request_type: 'PROJECT_EDITOR',
        status: 'PENDING',
        requester_user_id: null,
        target_user_id: null,
        requested_role_id: null,
        scope_type: 'PROJECT',
        scope_id: 'project-1',
        organisation_id: null,
        project_id: 'project-1',
        reason: null,
        decision_note: null,
        reviewed_by_user_id: null,
        reviewed_at: null,
        created_on: null,
        updated_on: null,
        requester_email: 'user@example.com',
        requester_display_name: 'New editor',
        organisation_name: null,
        project_name: 'Bridge project',
      },
    ]);
  });

  it('shows scoped pending access requests and links project admins to review them', async () => {
    render(<ProjectsPage role="Project admin" data={[]} />);

    await waitFor(() => {
      expect(screen.getByText('Pending access requests (1)')).toBeTruthy();
    });
    fireEvent.click(screen.getByText('Pending access requests (1)'));
    fireEvent.click(await screen.findByText('New editor'));

    expect(navigateMock).toHaveBeenCalledWith('/ManageUserAccess/admin');
  });

  it('links organisation admins to their request review screen', async () => {
    vi.mocked(accessRequestsService.fetchPending).mockResolvedValue([
      {
        id: 'request-org',
        request_type: 'PROJECT_ADMIN',
        status: 'PENDING',
        requester_user_id: null,
        target_user_id: null,
        requested_role_id: null,
        scope_type: 'PROJECT',
        scope_id: 'project-1',
        organisation_id: 'org-1',
        project_id: 'project-1',
        reason: null,
        decision_note: null,
        reviewed_by_user_id: null,
        reviewed_at: null,
        created_on: null,
        updated_on: null,
        requester_email: 'admin@example.com',
        requester_display_name: 'Project admin applicant',
        organisation_name: 'Organisation',
        project_name: 'Bridge project',
      },
    ]);

    render(<ProjectsPage role="Org admin" data={[]} />);

    await waitFor(() => expect(screen.getByText('Pending access requests (1)')).toBeTruthy());
    fireEvent.click(screen.getByText('Pending access requests (1)'));
    fireEvent.click(await screen.findByText('Project admin applicant'));

    expect(navigateMock).toHaveBeenCalledWith('/ManageUserAccess/orgadmin');
  });

  it('does not load admin indicators for ordinary users', () => {
    render(<ProjectsPage role="user" data={[]} />);

    expect(accessRequestsService.fetchPending).not.toHaveBeenCalled();
    expect(screen.queryByText(/Pending access requests/)).toBeNull();
  });
});
