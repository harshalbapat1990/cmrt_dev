import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import http from '@/http';
import ProjectDatasetsSelectPage from './ProjectDatasetsSelectPage';

vi.mock('@/http', () => ({
  default: { get: vi.fn() },
}));

describe('ProjectDatasetsSelectPage', () => {
  beforeEach(() => {
    vi.mocked(http.get).mockResolvedValue({
      data: [{
        id: 'project-1',
        project_name: 'Bridge renewal',
        dataset_revision_counts: {
          draft: 1,
          published: 0,
          deprecated: 2,
          archived: 0,
        },
      }],
    });
  });

  it('shows each lifecycle count on the project card and preserves its link', async () => {
    render(
      <MemoryRouter>
        <ProjectDatasetsSelectPage />
      </MemoryRouter>,
    );

    expect(await screen.findByText('Bridge renewal')).toBeTruthy();
    expect(screen.getByText('1 draft')).toBeTruthy();
    expect(screen.getByText('0 published')).toBeTruthy();
    expect(screen.getByText('2 deprecated')).toBeTruthy();
    expect(screen.getByText('0 archived')).toBeTruthy();
    expect(screen.getByRole('link', { name: /Bridge renewal/ }).getAttribute('href'))
      .toBe('/datasets/project/project-1');
  });
});
