import http from '@/http';

export type TermsDocumentType = 'PICS' | 'TERMS_OF_USE';

export interface TermsDocumentVersion {
    id: string;
    document_type: TermsDocumentType;
    version: number;
    filename: string;
    file_size: number;
    storage_backend: string;
    uploaded_by_id: string | null;
    uploaded_at: string;
    is_active: boolean;
}

class TermsDocumentsService {
    async getActiveVersion(documentType: TermsDocumentType): Promise<TermsDocumentVersion | null> {
        try {
            const response = await http.get(`/api/terms-documents/${documentType}`);
            return response.data as TermsDocumentVersion;
        } catch (err: any) {
            if (err?.response?.status === 404) return null;
            throw err;
        }
    }

    async getAllVersions(documentType: TermsDocumentType): Promise<TermsDocumentVersion[]> {
        const response = await http.get(`/api/terms-documents/${documentType}/versions`);
        return response.data as TermsDocumentVersion[];
    }

    async fetchFileBlobUrl(documentType: TermsDocumentType, docId: string): Promise<string> {
        const response = await http.get(`/api/terms-documents/${documentType}/${docId}/file`, {
            responseType: 'blob',
        });
        return URL.createObjectURL(response.data as Blob);
    }

    async uploadPdf(documentType: TermsDocumentType, file: File): Promise<TermsDocumentVersion> {
        const formData = new FormData();
        formData.append('file', file);
        const response = await http.post(`/api/terms-documents/${documentType}/upload`, formData, {
            headers: { 'Content-Type': 'multipart/form-data' },
        });
        return response.data as TermsDocumentVersion;
    }

    async activateVersion(documentType: TermsDocumentType, docId: string): Promise<TermsDocumentVersion> {
        const response = await http.put(`/api/terms-documents/${documentType}/${docId}/activate`, {});
        return response.data as TermsDocumentVersion;
    }
}

export default new TermsDocumentsService();
