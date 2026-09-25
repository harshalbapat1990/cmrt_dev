import http from '@/http';
import BaseService from './base.service';

export interface UserGuideVersion {
    id: string;
    version: number;
    filename: string;
    file_size: number;
    storage_backend: string;
    uploaded_by_id: string | null;
    uploaded_at: string;
    is_active: boolean;
}

class UserGuideService extends BaseService {
    constructor() {
        super('/api/user-guide');
    }

    async getActiveVersion(): Promise<UserGuideVersion | null> {
        try {
            const response = await this.get('/');
            return response.data as UserGuideVersion;
        } catch (err: any) {
            if (err?.response?.status === 404) return null;
            throw err;
        }
    }

    async getAllVersions(): Promise<UserGuideVersion[]> {
        const response = await this.get('/versions');
        return response.data as UserGuideVersion[];
    }

    async fetchFileBlobUrl(guideId: string): Promise<string> {
        const response = await http.get(`/api/user-guide/${guideId}/file`, {
            responseType: 'blob',
        });
        return URL.createObjectURL(response.data as Blob);
    }

    async uploadPdf(file: File): Promise<UserGuideVersion> {
        const formData = new FormData();
        formData.append('file', file);
        const response = await http.post('/api/user-guide/upload', formData, {
            headers: { 'Content-Type': 'multipart/form-data' },
        });
        return response.data as UserGuideVersion;
    }

    async activateVersion(guideId: string): Promise<UserGuideVersion> {
        const response = await this.put(`/${guideId}/activate`);
        return response.data as UserGuideVersion;
    }
}

export default new UserGuideService();
