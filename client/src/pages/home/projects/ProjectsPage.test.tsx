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
    expect(http.get).not.toHaveBeenCalled();
    expect(screen.queryByText(/Pending access requests/)).toBeNull();
  });

  it('shows option and period submissions and links a period with its period ID', async () => {
    vi.mocked(http.get).mockResolvedValue({ data: [
      {
        project_id: 'project-1', project_name: 'Design project', stage_instance_id: 'design-stage',
        stage: 'DESIGN', report_number: 2, num_reports_required: 2, approval_status: 'submitted',
        workflow_source: 'project_option', period_id: null, period_label: null,
      },
      {
        project_id: 'project-2', project_name: 'Recurring project', stage_instance_id: 'recurring-stage',
        stage: 'RECURRING', report_number: null, num_reports_required: 1, approval_status: 'awaiting_approval',
        workflow_source: 'reporting_period', period_id: 'period-1', period_label: 'Mar 2027',
      },
    ] });

    render(<ProjectsPage role="Project admin" data={[]} />);

    expect(await screen.findByText('Pending approvals (2)')).toBeTruthy();
    fireEvent.click(screen.getByText('Pending approvals (2)'));
    fireEvent.click(await screen.findByText('Recurring — Mar 2027'));

    expect(navigateMock).toHaveBeenCalledWith(
      '/dataEntry?projectId=project-2&stageInstanceId=recurring-stage&periodId=period-1',
    );
    expect(screen.getByText('Design (2 of 2)')).toBeTruthy();
  });

  it('shows period reopen requests and keeps project-option reopen navigation', async () => {
    vi.mocked(http.get).mockResolvedValue({ data: [
      {
        project_id: 'project-3', project_name: 'Construction project', stage_instance_id: 'construction-stage',
        stage: 'CONSTRUCTION', report_number: null, num_reports_required: 1, approval_status: 'reopen_requested',
        workflow_source: 'reporting_period', period_id: 'period-2', period_label: 'Apr 2027',
      },
      {
        project_id: 'project-4', project_name: 'Business case project', stage_instance_id: 'bc-stage',
        stage: 'BUSINESS_CASE', report_number: 1, num_reports_required: 1, approval_status: 'pending_reopen',
        workflow_source: 'project_option', period_id: null, period_label: null,
      },
    ] });

    render(<ProjectsPage role="Org admin" data={[]} />);

    expect(await screen.findByText('Pending reopen requests (2)')).toBeTruthy();
    fireEvent.click(screen.getByText('Pending reopen requests (2)'));
    fireEvent.click(await screen.findByText('Construction — Apr 2027'));

    expect(navigateMock).toHaveBeenCalledWith(
      '/dataEntry?projectId=project-3&stageInstanceId=construction-stage&periodId=period-2',
    );
    expect(screen.getByText('Business Case')).toBeTruthy();
  });

  it('shows an API failure instead of presenting a zero pending-action count', async () => {
    vi.mocked(http.get).mockRejectedValue(new Error('server unavailable'));

    render(<ProjectsPage role="Project admin" data={[]} />);

    expect(await screen.findByText('Pending approvals (—)')).toBeTruthy();
    fireEvent.click(screen.getByText('Pending approvals (—)'));
    expect(await screen.findByText('Could not load pending approvals.')).toBeTruthy();
  });
});
