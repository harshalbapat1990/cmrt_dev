import BaseService from './base.service';

export interface UserGuideVideo {
    id: string;
    title: string;
    youtube_url: string;
    youtube_video_id: string;
    created_by_id: string | null;
    created_at: string;
    is_published: boolean;
}

class UserGuideVideoService extends BaseService {
    constructor() {
        super('/api/user-guide-videos');
    }

    async getPublishedVideos(): Promise<UserGuideVideo[]> {
        const response = await this.get('/');
        return response.data as UserGuideVideo[];
    }

    async getAllVideos(): Promise<UserGuideVideo[]> {
        const response = await this.get('/all');
        return response.data as UserGuideVideo[];
    }

    async createVideo(
        title: string,
        youtubeUrl: string,
    ): Promise<UserGuideVideo> {
        const response = await this.post('/', {
            title,
            youtube_url: youtubeUrl,
        });

        return response.data as UserGuideVideo;
    }

    async publishVideo(
        videoId: string,
    ): Promise<UserGuideVideo> {
        const response = await this.put(
            `/${videoId}/publish`,
        );

        return response.data as UserGuideVideo;
    }

    async unpublishVideo(
        videoId: string,
    ): Promise<UserGuideVideo> {
        const response = await this.put(
            `/${videoId}/unpublish`,
        );

        return response.data as UserGuideVideo;
    }

    async deleteVideo(
        videoId: string,
    ): Promise<void> {
        await this.delete(`/${videoId}`);
    }
}

export default new UserGuideVideoService();