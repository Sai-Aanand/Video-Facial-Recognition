import axios from 'axios';
import type { UploadResponse, VideoRecord } from '../types';

const api = axios.create({
  baseURL: '/api',
});

export async function listVideos(): Promise<VideoRecord[]> {
  const { data } = await api.get<VideoRecord[]>('/videos');
  return data;
}

export interface UploadPayload {
  file?: File | null;
  videoPath?: string;
}

export async function uploadVideo(payload: UploadPayload): Promise<UploadResponse> {
  const formData = new FormData();

  if (payload.file) {
    formData.append('file', payload.file);
  }
  if (payload.videoPath) {
    formData.append('video_path', payload.videoPath);
  }

  const { data } = await api.post<UploadResponse>('/videos/upload', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  });
  return data;
}

export async function getVideo(videoId: string): Promise<VideoRecord> {
  const { data } = await api.get<VideoRecord>(`/videos/${videoId}`);
  return data;
}
