import { useCallback, useEffect, useRef, useState } from 'react';
import { useUser } from '@/context/UserContext';
import UserGuideService, { type UserGuideVersion } from '@/services/UserGuide.service';
import UserGuideVideoService, {type UserGuideVideo,} from '@/services/UserGuideVideo.service';
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

function getYoutubeThumbnail(videoId: string): string {
    return `https://img.youtube.com/vi/${videoId}/hqdefault.jpg`;
}

export default function UserGuidePage() {
    const { roles } = useUser();
    const isSuperAdmin = roles.includes('SUPER_ADMIN');

    const [active, setActive] = useState<UserGuideVersion | null>(null);
    const [blobUrl, setBlobUrl] = useState<string | null>(null);
    const [versions, setVersions] = useState<UserGuideVersion[]>([]);
    const [videos, setVideos] = useState<UserGuideVideo[]>([]);
    const [videoTitle, setVideoTitle] = useState('');
    const [videoUrl, setVideoUrl] = useState('');
    const [videoError, setVideoError] = useState<string | null>(null);
    const [savingVideo, setSavingVideo] = useState(false);
    const [videoActionId, setVideoActionId] = useState<string | null>(null);
    const [showVideoModal, setShowVideoModal] = useState(false);
    const [loading, setLoading] = useState(true);
    const [expanded, setExpanded] = useState(!isSuperAdmin);
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
            const [
                activeVersion,
                allVersions,
                loadedVideos,
            ] = await Promise.all([
                UserGuideService.getActiveVersion(),
                isSuperAdmin
                    ? UserGuideService.getAllVersions()
                    : Promise.resolve([]),
                isSuperAdmin
                    ? UserGuideVideoService.getAllVideos()
                    : UserGuideVideoService.getPublishedVideos(),
            ]);
            setActive(activeVersion);
            setVersions(allVersions);
            setVideos(loadedVideos);
            if (activeVersion) {
                const url = await UserGuideService.fetchFileBlobUrl(activeVersion.id);
                setAndTrackBlobUrl(url);
            } else {
                setAndTrackBlobUrl(null);
            }
        } catch {
            setError('Failed to load User Guide. Please try again.');
        } finally {
            setLoading(false);
        }
    }, [isSuperAdmin]);

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
            await UserGuideService.uploadPdf(file);
            await load();
        } catch (err: any) {
            setUploadError(extractApiError(err, 'Upload failed. Please try again.'));
        } finally {
            setUploading(false);
        }
    };

    const handleActivate = async (guideId: string) => {
        setActivating(guideId);
        try {
            await UserGuideService.activateVersion(guideId);
            await load();
        } catch {
            setError('Failed to activate version. Please try again.');
        } finally {
            setActivating(null);
        }
    };

    const handleCreateVideo = async () => {
        if (!videoTitle.trim() || !videoUrl.trim()) {
            setVideoError('Title and YouTube URL are required.');
            return;
        }

        setSavingVideo(true);
        setVideoError(null);

        try {
            await UserGuideVideoService.createVideo(
                videoTitle,
                videoUrl,
            );

            setVideoTitle('');
            setVideoUrl('');

            await load();
        } catch (err: any) {
            setVideoError(
                extractApiError(
                    err,
                    'Failed to create video.',
                ),
            );
        } finally {
            setSavingVideo(false);
        }
    };

    const handlePublishVideo = async (
        videoId: string,
    ) => {
        setVideoActionId(videoId);

        try {
            await UserGuideVideoService.publishVideo(
                videoId,
            );

            await load();
        } finally {
            setVideoActionId(null);
        }
    };

    const handleUnpublishVideo = async (
        videoId: string,
    ) => {
        setVideoActionId(videoId);

        try {
            await UserGuideVideoService.unpublishVideo(
                videoId,
            );

            await load();
        } finally {
            setVideoActionId(null);
        }
    };

    const handleDeleteVideo = async (
        videoId: string,
    ) => {
        if (!confirm('Delete this video?')) {
            return;
        }

        setVideoActionId(videoId);

        try {
            await UserGuideVideoService.deleteVideo(
                videoId,
            );

            await load();
        } finally {
            setVideoActionId(null);
        }
    };

    if (loading) {
        return (
            <div className="flex items-center justify-center h-64 text-slate-400">
                Loading User Guide…
            </div>
        );
    }

    return (
        <div className="flex flex-col gap-6 p-6 max-w-6xl mx-auto">
            <div className="flex items-center justify-between">
                <h1 className="text-2xl font-semibold text-slate-800">User Guide</h1>
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
                    {isSuperAdmin && (
                        <>
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
                                {uploading ? 'Uploading…' : 'Upload New Guide Version'}
                            </button>
                            {/* <button
                                onClick={() => fileInputRef.current?.click()}
                                disabled={uploading}
                                className="inline-flex items-center gap-2 rounded-md bg-green-700 px-4 py-2 text-sm font-medium text-white cursor-pointer shadow-sm hover:bg-green-800 disabled:opacity-60 transition-colors"
                            >
                                <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                                    <path strokeLinecap="round" strokeLinejoin="round" d="M4 16v2a2 2 0 002 2h12a2 2 0 002-2v-2M7 10l5-5m0 0l5 5M12 4v12" />
                                </svg>
                                {uploading ? 'Uploading…' : 'Upload New Video'}
                            </button> */}
                            <button
                                onClick={() => setShowVideoModal(true)}
                                className="inline-flex items-center gap-2 rounded-md bg-green-700 px-4 py-2 text-sm font-medium text-white cursor-pointer shadow-sm hover:bg-green-800"
                            >
                                Upload New Video
                            </button>
                        </>
                    )}
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

            {active && blobUrl ? (
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
                            style={{ height: 'calc(100vh - 300px)', minHeight: '500px' }}
                        />
                    )}
                </div>
            ) : (
                <div className="flex flex-col items-center justify-center rounded-lg border border-dashed border-slate-300 bg-slate-50 py-20 text-center">
                    <svg className="mb-3 h-12 w-12 text-slate-300" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                        <path strokeLinecap="round" strokeLinejoin="round" d="M19.5 14.25v-2.625a3.375 3.375 0 00-3.375-3.375h-1.5A1.125 1.125 0 0113.5 7.125v-1.5a3.375 3.375 0 00-3.375-3.375H8.25m2.25 0H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 00-9-9z" />
                    </svg>
                    <p className="text-sm font-medium text-slate-500">No User Guide available yet.</p>
                    {isSuperAdmin && (
                        <p className="mt-1 text-xs text-slate-400">Use the "Upload New Guide Version" button to publish the guide.</p>
                    )}
                </div>
            )}
            <div className="rounded-lg border border-slate-200 bg-white shadow-sm p-6">
                <h2 className="text-lg font-semibold text-slate-800 mb-4">
                    User Guide Videos
                </h2>

                {videos.length === 0 ? (
                    <p className="text-sm text-slate-500">
                        No videos available.
                    </p>
                ) : (
                    <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
                        {videos
                            .filter(v => v.is_published || isSuperAdmin)
                            .map(video => (
                                <div
                                    key={video.id}
                                    className="overflow-hidden rounded-lg border border-slate-200"
                                >
                                    <a
                                        href={video.youtube_url}
                                        target="_blank">
                                        <img
                                            src={getYoutubeThumbnail(video.youtube_video_id)}
                                            alt={video.title}
                                            className="w-full"
                                        />

                                        <div className="p-3">
                                            <div className="font-medium text-slate-700">
                                                {video.title}
                                            </div>
                                        </div>
                                    </a>
                                </div>
                            ))}
                    </div>
                )}
            </div>
            {isSuperAdmin && versions.length > 0 && (
                <div className="rounded-lg border border-slate-200 shadow-sm overflow-hidden bg-white">
                    <div className="border-b border-slate-200 px-4 py-3">
                        <h2 className="text-sm font-semibold text-slate-700">Version History</h2>
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

            {isSuperAdmin && (
                <div className="rounded-lg border border-slate-200 shadow-sm overflow-hidden bg-white">
                    <div className="border-b border-slate-200 px-4 py-3">
                        <h2 className="text-sm font-semibold text-slate-700">
                            User Guide Video Library
                        </h2>
                    </div>
                    <table className="w-full text-sm">
                        <thead className="bg-slate-50 text-xs font-medium text-slate-500 uppercase tracking-wide">
                            <tr>
                                <th className="px-4 py-2 text-left">Title</th>
                                <th className="px-4 py-2 text-left">Uploaded</th>
                                <th className="px-4 py-2 text-left">Status</th>
                                <th className="px-4 py-2 text-left">Action</th>
                            </tr>
                        </thead>
                        <tbody className="divide-y divide-slate-100">
                            {videos.map(v => (
                                <tr
                                    key={v.id}
                                    className={
                                        v.is_published
                                            ? 'bg-green-50'
                                            : 'hover:bg-slate-50'
                                    }
                                >
                                    <td className="px-4 py-2 text-slate-700">
                                        {v.title}
                                    </td>

                                    <td className="px-4 py-2 text-slate-500">
                                        {formatDate(v.created_at)}
                                    </td>

                                    <td className="px-4 py-2">
                                        {v.is_published ? (
                                            <span className="inline-flex items-center rounded-full bg-green-100 px-2 py-0.5 text-xs font-medium text-green-800">
                                                Published
                                            </span>
                                        ) : (
                                            <span className="inline-flex items-center rounded-full bg-slate-100 px-2 py-0.5 text-xs font-medium text-slate-500">
                                                Unpublished
                                            </span>
                                        )}
                                    </td>

                                    <td className="px-4 py-2">
                                        {v.is_published ? (
                                            <button
                                                onClick={() =>
                                                    handleUnpublishVideo(v.id)
                                                }
                                                disabled={videoActionId === v.id}
                                                className="text-xs font-medium text-orange-700 hover:text-orange-900 cursor-pointer"
                                            >
                                                Unpublish
                                            </button>
                                        ) : (
                                            <button
                                                onClick={() =>
                                                    handlePublishVideo(v.id)
                                                }
                                                disabled={videoActionId === v.id}
                                                className="text-xs font-medium text-green-700 hover:text-green-900 cursor-pointer"
                                            >
                                                Publish
                                            </button>
                                        )}

                                        <button
                                            onClick={() =>
                                                handleDeleteVideo(v.id)
                                            }
                                            className="ml-4 text-xs font-medium text-red-700 hover:text-red-900 cursor-pointer"
                                        >
                                            Delete
                                        </button>
                                    </td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                </div>
            )}
            {showVideoModal && (
                <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
                    <div className="w-full max-w-lg rounded-lg bg-white shadow-xl">
                        <div className="border-b px-6 py-4">
                            <h3 className="text-lg font-semibold">
                                Upload User Guide Video
                            </h3>
                        </div>

                        <div className="space-y-4 p-6">
                            <div>
                                <label className="block text-sm font-medium text-slate-700">
                                    Title
                                </label>

                                <input
                                    type="text"
                                    value={videoTitle}
                                    onChange={e => setVideoTitle(e.target.value)}
                                    className="mt-1 w-full rounded border border-slate-300 px-3 py-2"
                                />
                            </div>

                            <div>
                                <label className="block text-sm font-medium text-slate-700">
                                    YouTube URL
                                </label>

                                <input
                                    type="text"
                                    value={videoUrl}
                                    onChange={e => setVideoUrl(e.target.value)}
                                    className="mt-1 w-full rounded border border-slate-300 px-3 py-2"
                                />
                            </div>

                            {videoError && (
                                <div className="text-sm text-red-600">
                                    {videoError}
                                </div>
                            )}
                        </div>

                        <div className="flex justify-end gap-3 border-t px-6 py-4">
                            <button
                                onClick={() => setShowVideoModal(false)}
                                className="rounded border border-slate-300 px-4 py-2"
                            >
                                Cancel
                            </button>

                            <button
                                onClick={async () => {
                                    await handleCreateVideo();
                                    setShowVideoModal(false);
                                }}
                                disabled={savingVideo}
                                className="rounded bg-green-700 px-4 py-2 text-white"
                            >
                                {savingVideo ? 'Saving...' : 'Upload'}
                            </button>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
}
