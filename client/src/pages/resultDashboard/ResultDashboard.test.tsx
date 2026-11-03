import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import ResultDashboard from './ResultDashboard';

const { mockStageInstances } = vi.hoisted(() => ({
  mockStageInstances: [
    { id: 'business-stage', stage: 'BUSINESS_CASE', num_reports_required: 1 },
    { id: 'design-stage', stage: 'DESIGN', num_reports_required: 1 },
  ],
}));

vi.mock('react-router-dom', () => ({
  useLocation: () => ({ state: null }),
  useNavigate: () => vi.fn(),
  useSearchParams: () => [new URLSearchParams('projectId=project-1')],
}));

vi.mock('@/context/ProjectHeaderContext', () => ({
  useProjectHeader: () => ({ setProjectHeader: vi.fn(), clearProjectHeader: vi.fn() }),
}));

vi.mock('./useProjectDashboardProject', () => ({
  useProjectDashboardProject: () => ({
    project: {
      id: 'project-1',
      name: 'Test project',
      project_class: 'SMALL',
      stage_instances: mockStageInstances,
    },
    loading: false,
    error: null,
  }),
}));

vi.mock('@/customHooks/useProjectStageAccess', () => ({
  useProjectStageAccess: () => ({ stageAccess: [], loading: false, error: null }),
}));

vi.mock('../smallProject/dataEntry/stageAccessUi', () => ({
  filterAccessibleStageInstances: (instances: unknown[]) => instances,
}));

vi.mock('../smallProject/dataEntry/stageNavigationOptions', () => ({
  buildDataEntryStageUrl: () => null,
  buildStageNavigationOptions: () => [],
  RESULTS_DASHBOARD_VALUE: 'results-dashboard',
}));

vi.mock('../smallProject/dataEntry/dataEntryTypes', () => ({
  normalizeProjectClass: (value: string) => value === 'SMALL' ? 'Small' : value,
}));

vi.mock('../../components/common/Select', () => ({
  SelectListbox: ({ value, options, onChange, placeholder }: {
    value: string;
    options: Array<{ label: string; value: string }>;
    onChange: (value: string) => void;
    placeholder?: string;
  }) => (
    <select aria-label={placeholder} value={value} onChange={(event) => onChange(event.target.value)}>
      <option value="">{placeholder}</option>
      {options.map((option) => <option key={option.value} value={option.value}>{option.label}</option>)}
    </select>
  ),
}));

vi.mock('@/services/ProjectOptions.service', () => ({
  default: { fetchOptions: vi.fn().mockResolvedValue([{ id: 'option-1', label: 'Option 1', report_number: 1 }]) },
}));

vi.mock('@/services/ConstructionPeriods.service', () => ({
  ConstructionPeriodsService: { listPeriods: vi.fn().mockResolvedValue([]) },
}));

vi.mock('./EmissionsBreakdownTab', () => ({ default: () => null }));
vi.mock('./MaterialHotspotsTab', () => ({ default: () => null }));
vi.mock('./MitigationSummaryTab', () => ({ default: () => null }));
vi.mock('./RenewableEnergyTab', () => ({ default: () => null }));
vi.mock('./OffsettingMeasuresTab', () => ({ default: () => null }));
vi.mock('./Comparison', () => ({ default: () => null }));
vi.mock('./ComparisonByOption', () => ({ default: () => null }));
vi.mock('./WasteAndRecycleTab', () => ({ default: () => null }));
vi.mock('./LcaModuleBreakdownTab', () => ({ default: () => null }));
vi.mock('./RatingPerformance', () => ({ default: () => null }));
vi.mock('./DetailedResultsTab', () => ({ default: () => null }));

describe('ResultDashboard submission selection', () => {
  beforeEach(() => vi.clearAllMocks());

  it('retains the selected submission while navigating dashboard sections', async () => {
    render(<ResultDashboard />);

    const submission = screen.getByLabelText('Submission') as HTMLSelectElement;
    fireEvent.change(submission, { target: { value: 'BUSINESS_CASE_1' } });
    await waitFor(() => expect(submission.value).toBe('BUSINESS_CASE_1'));

    fireEvent.click(screen.getByRole('button', { name: 'Materials hotspots' }));

    expect(screen.getByLabelText('Submission')).toHaveProperty('value', 'BUSINESS_CASE_1');
  });
});
