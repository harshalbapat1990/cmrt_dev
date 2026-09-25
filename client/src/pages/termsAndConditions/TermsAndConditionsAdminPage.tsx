import { useCallback, useEffect, useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useUser } from '@/context/UserContext';
import TermsDocumentsService, {
    type TermsDocumentType,
    type TermsDocumentVersion,
} from '@/services/TermsDocuments.service';
import { extractApiError } from '@/utils/utils';

function formatBytes(bytes: number): string {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

function formatDate(iso: string): string {
    return new Date(iso).toLocaleString(undefined, {
        year: 'numeric', month: 'short', day: 'numeric',
        hour: '2-digit', minute: '2-digit',
    });
}

type SectionProps = {
    documentType: TermsDocumentType;
    title: string;
};

function TermsDocumentSection({ documentType, title }: SectionProps) {
    const [active, setActive] = useState<TermsDocumentVersion | null>(null);
    const [blobUrl, setBlobUrl] = useState<string | null>(null);
    const [versions, setVersions] = useState<TermsDocumentVersion[]>([]);
    const [loading, setLoading] = useState(true);
    const [expanded, setExpanded] = useState(false);
    const [uploading, setUploading] = useState(false);
    const [activating, setActivating] = useState<string | null>(null);
    const [error, setError] = useState<string | null>(null);
    const [uploadError, setUploadError] = useState<string | null>(null);
    const fileInputRef = useRef<HTMLInputElement>(null);
    const blobUrlRef = useRef<string | null>(null);

    const setAndTrackBlobUrl = (url: string | null) => {
        if (blobUrlRef.current) URL.revokeObjectURL(blobUrlRef.current);
        blobUrlRef.current = url;
        setBlobUrl(url);
    };

    useEffect(() => () => { if (blobUrlRef.current) URL.revokeObjectURL(blobUrlRef.current); }, []);

    const load = useCallback(async () => {
        setLoading(true);
        setError(null);
        try {
            const [activeVersion, allVersions] = await Promise.all([
                TermsDocumentsService.getActiveVersion(documentType),
                TermsDocumentsService.getAllVersions(documentType),
            ]);
            setActive(activeVersion);
            setVersions(allVersions);
            if (activeVersion) {
                const url = await TermsDocumentsService.fetchFileBlobUrl(documentType, activeVersion.id);
                setAndTrackBlobUrl(url);
            } else {
                setAndTrackBlobUrl(null);
            }
        } catch {
            setError('Failed to load document. Please try again.');
        } finally {
            setLoading(false);
        }
    }, [documentType]);

    useEffect(() => { load(); }, [load]);

    const handleFileSelect = async (e: React.ChangeEvent<HTMLInputElement>) => {
        const file = e.target.files?.[0];
        if (!file) return;
        e.target.value = '';

        if (!file.name.toLowerCase().endsWith('.pdf')) {
            setUploadError('Only PDF files are accepted.');
            return;
        }

        setUploadError(null);
        setUploading(true);
        try {
            await TermsDocumentsService.uploadPdf(documentType, file);
            await load();
        } catch (err: any) {
            setUploadError(extractApiError(err, 'Upload failed. Please try again.'));
        } finally {
            setUploading(false);
        }
    };

    const handleActivate = async (docId: string) => {
        setActivating(docId);
        try {
            await TermsDocumentsService.activateVersion(documentType, docId);
            await load();
        } catch {
            setError('Failed to activate version. Please try again.');
        } finally {
            setActivating(null);
        }
    };

    return (
        <div className="flex flex-col gap-4">
            <div className="flex items-center justify-between">
                <h2 className="text-xl font-semibold text-slate-800">{title}</h2>
                <div className="flex items-center gap-3">
                    {active && blobUrl && (
                        <a
                            href={blobUrl}
                            download={active.filename}
                            className="inline-flex items-center gap-2 rounded-md border border-slate-300 bg-white px-4 py-2 text-sm font-medium text-slate-700 shadow-sm hover:bg-slate-50 transition-colors"
                        >
                            <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                                <path strokeLinecap="round" strokeLinejoin="round" d="M4 16v2a2 2 0 002 2h12a2 2 0 002-2v-2M7 10l5 5m0 0l5-5m-5 5V4" />
                            </svg>
                            Download PDF
                        </a>
                    )}
                    <input
                        ref={fileInputRef}
                        type="file"
                        accept="application/pdf,.pdf"
                        className="hidden"
                        onChange={handleFileSelect}
                    />
                    <button
                        onClick={() => fileInputRef.current?.click()}
                        disabled={uploading}
                        className="inline-flex items-center gap-2 rounded-md bg-green-700 px-4 py-2 text-sm font-medium text-white cursor-pointer shadow-sm hover:bg-green-800 disabled:opacity-60 transition-colors"
                    >
                        <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                            <path strokeLinecap="round" strokeLinejoin="round" d="M4 16v2a2 2 0 002 2h12a2 2 0 002-2v-2M7 10l5-5m0 0l5 5M12 4v12" />
                        </svg>
                        {uploading ? 'Uploading…' : 'Upload New Version'}
                    </button>
                </div>
            </div>

            {error && (
                <div className="rounded-md bg-red-50 border border-red-200 px-4 py-3 text-sm text-red-700">
                    {error}
                </div>
            )}
            {uploadError && (
                <div className="rounded-md bg-red-50 border border-red-200 px-4 py-3 text-sm text-red-700">
                    {uploadError}
                </div>
            )}

            {loading ? (
                <div className="flex items-center justify-center h-32 text-slate-400">Loading…</div>
            ) : active && blobUrl ? (
                <div className="rounded-lg border border-slate-200 shadow-sm overflow-hidden bg-white">
                    <button
                        onClick={() => setExpanded(e => !e)}
                        className="flex w-full items-center justify-between px-4 py-3 border-b border-slate-200 hover:bg-slate-50 transition-colors cursor-pointer"
                    >
                        <span className="text-sm font-semibold text-slate-700">
                            {active.filename}
                        </span>
                        <svg
                            className={`h-4 w-4 text-slate-400 transition-transform duration-200 ${expanded ? 'rotate-180' : ''}`}
                            fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}
                        >
                            <path strokeLinecap="round" strokeLinejoin="round" d="M19 9l-7 7-7-7" />
                        </svg>
                    </button>
                    {expanded && (
                        <embed
                            src={blobUrl}
                            type="application/pdf"
                            className="w-full"
                            style={{ height: 'calc(100vh - 500px)', minHeight: '400px' }}
                        />
                    )}
                </div>
            ) : (
                <div className="flex flex-col items-center justify-center rounded-lg border border-dashed border-slate-300 bg-slate-50 py-16 text-center">
                    <svg className="mb-3 h-10 w-10 text-slate-300" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                        <path strokeLinecap="round" strokeLinejoin="round" d="M19.5 14.25v-2.625a3.375 3.375 0 00-3.375-3.375h-1.5A1.125 1.125 0 0113.5 7.125v-1.5a3.375 3.375 0 00-3.375-3.375H8.25m2.25 0H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 00-9-9z" />
                    </svg>
                    <p className="text-sm font-medium text-slate-500">No document uploaded yet.</p>
                    <p className="mt-1 text-xs text-slate-400">Use "Upload New Version" to publish this document.</p>
                </div>
            )}

            {versions.length > 0 && (
                <div className="rounded-lg border border-slate-200 shadow-sm overflow-hidden bg-white">
                    <div className="border-b border-slate-200 px-4 py-3">
                        <h3 className="text-sm font-semibold text-slate-700">Version History</h3>
                    </div>
                    <table className="w-full text-sm">
                        <thead className="bg-slate-50 text-xs font-medium text-slate-500 uppercase tracking-wide">
                            <tr>
                                <th className="px-4 py-2 text-left">Version</th>
                                <th className="px-4 py-2 text-left">Filename</th>
                                <th className="px-4 py-2 text-left">Size</th>
                                <th className="px-4 py-2 text-left">Uploaded</th>
                                <th className="px-4 py-2 text-left">Status</th>
                                <th className="px-4 py-2 text-left">Action</th>
                            </tr>
                        </thead>
                        <tbody className="divide-y divide-slate-100">
                            {versions.map((v) => (
                                <tr key={v.id} className={v.is_active ? 'bg-green-50' : 'hover:bg-slate-50'}>
                                    <td className="px-4 py-2 font-mono text-slate-600">v{v.version}</td>
                                    <td className="px-4 py-2 text-slate-700 max-w-xs truncate" title={v.filename}>
                                        {v.filename}
                                    </td>
                                    <td className="px-4 py-2 text-slate-500">{formatBytes(v.file_size)}</td>
                                    <td className="px-4 py-2 text-slate-500">{formatDate(v.uploaded_at)}</td>
                                    <td className="px-4 py-2">
                                        {v.is_active ? (
                                            <span className="inline-flex items-center rounded-full bg-green-100 px-2 py-0.5 text-xs font-medium text-green-800">
                                                Active
                                            </span>
                                        ) : (
                                            <span className="inline-flex items-center rounded-full bg-slate-100 px-2 py-0.5 text-xs font-medium text-slate-500">
                                                Inactive
                                            </span>
                                        )}
                                    </td>
                                    <td className="px-4 py-2">
                                        {!v.is_active && (
                                            <button
                                                onClick={() => handleActivate(v.id)}
                                                disabled={activating === v.id}
                                                className="text-xs font-medium text-green-700 hover:text-green-900 disabled:opacity-50 cursor-pointer"
                                            >
                                                {activating === v.id ? 'Setting…' : 'Set active'}
                                            </button>
                                        )}
                                    </td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                </div>
            )}
        </div>
    );
}

export default function TermsAndConditionsAdminPage() {
    const { roles, isLoaded } = useUser();
    const navigate = useNavigate();
    const isSuperAdmin = roles.includes('SUPER_ADMIN');

    useEffect(() => {
        if (isLoaded && !isSuperAdmin) {
            navigate('/Home/user', { replace: true });
        }
    }, [isLoaded, isSuperAdmin, navigate]);

    if (!isLoaded || !isSuperAdmin) {
        return (
            <div className="flex items-center justify-center h-64 text-slate-400">
                {!isLoaded ? 'Loading…' : 'Redirecting…'}
            </div>
        );
    }

    return (
        <div className="flex flex-col gap-10 p-6 max-w-6xl mx-auto">
            <h1 className="text-2xl font-semibold text-slate-800">Terms &amp; Conditions</h1>
            <TermsDocumentSection documentType="PICS" title="Personal Information Collection Statement" />
            <hr className="border-slate-200" />
            <TermsDocumentSection documentType="TERMS_OF_USE" title="CMRT Terms of Use" />
        </div>
    );
}
