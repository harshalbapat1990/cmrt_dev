import BaseService from './base.service';
import type { BackgroundGradeMetric, BackgroundGradeMetricFilters } from '@/types/backgroundGradeMetrics';

export class BackgroundGradeMetricsService extends BaseService {
  constructor() {
    super('/api/background-grade-metrics');
  }

  async fetchMetrics(filters: BackgroundGradeMetricFilters = {}): Promise<BackgroundGradeMetric[]> {
    const params = new URLSearchParams();
    Object.entries(filters).forEach(([key, value]) => {
      if (value !== undefined && value !== null && value !== '') {
        params.append(key, String(value));
      }
    });
    const query = params.toString();
    const response = await this.get(query ? `?${query}` : '');
    return response.data as BackgroundGradeMetric[];
  }

  async fetchMetricById(id: string): Promise<BackgroundGradeMetric> {
    const response = await this.get(`/${id}`);
    return response.data as BackgroundGradeMetric;
  }
}

export default new BackgroundGradeMetricsService();
