import { fireEvent, render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import DatasetLifecycleModal from './DatasetLifecycleModal';

const boundProjects = [
  { project_id: 'project-a', project_name: 'North bridge' },
  { project_id: 'project-b', project_name: 'South road' },
];

describe('DatasetLifecycleModal', () => {
  it('lists bound projects and explains recalculation before unpublishing', () => {
    const onConfirm = vi.fn();
    render(
      <DatasetLifecycleModal
        mode="unpublish"
        projects={boundProjects}
        onClose={vi.fn()}
        onConfirm={onConfirm}
      />,
    );

    expect(screen.getByText('North bridge')).toBeTruthy();
    expect(screen.getByText('South road')).toBeTruthy();
    expect(screen.getByText(/recalculate emissions.*published again/i)).toBeTruthy();
    fireEvent.click(screen.getByRole('button', { name: 'Confirm and unpublish' }));
    expect(onConfirm).toHaveBeenCalledOnce();
  });

  it('blocks deprecation and exposes no confirm action while projects are bound', () => {
    render(
      <DatasetLifecycleModal
        mode="deprecate"
        projects={boundProjects}
        onClose={vi.fn()}
      />,
    );

    expect(screen.getByText(/cannot be deprecated while any project is using it/i)).toBeTruthy();
    expect(screen.queryByRole('button', { name: 'Confirm deprecation' })).toBeNull();
    expect(screen.getByRole('button', { name: 'Close' })).toBeTruthy();
  });

  it('shows per-project failures and missing-data warnings after publish', () => {
    render(
      <DatasetLifecycleModal
        mode="publish-report"
        recalculations={[
          {
            project_id: 'project-a',
            project_name: 'North bridge',
            status: 'failed',
            missing_data: [],
            calculation_errors: [{ entry: 'Road users', message: 'Factor lookup failed' }],
            recalculated_count: 0,
          },
          {
            project_id: 'project-b',
            project_name: 'South road',
            status: 'recalculated',
            missing_data: [{ entry: 'Drainage', dataset_table: 'Grade 2 factors' }],
            calculation_errors: [],
            recalculated_count: 3,
          },
        ]}
        onClose={vi.fn()}
      />,
    );

    expect(screen.getByText(/revision was published.*1 of 2/i)).toBeTruthy();
    expect(screen.getByText(/North bridge: recalculation failed/i)).toBeTruthy();
    expect(screen.getByText(/South road: recalculated/i)).toBeTruthy();
    expect(screen.getByText(/Grade 2 factors/)).toBeTruthy();
  });
});
