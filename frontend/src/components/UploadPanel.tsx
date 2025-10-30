import { FormEvent, useState } from 'react';
import { uploadVideo, UploadPayload } from '../api/client';
import type { UploadResponse } from '../types';

interface UploadPanelProps {
  onUploadComplete: (result: UploadResponse) => void;
  onUploadStart: () => void;
  onError: (message: string) => void;
}

export default function UploadPanel({ onUploadComplete, onUploadStart, onError }: UploadPanelProps) {
  const [file, setFile] = useState<File | null>(null);
  const [videoPath, setVideoPath] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!file && !videoPath) {
      onError('Provide a video file or a server-side video path.');
      return;
    }

    const normalizedPath = videoPath.trim().replace(/^['"]|['"]$/g, '');
    const payload: UploadPayload = { file, videoPath: normalizedPath || undefined };

    try {
      setIsSubmitting(true);
      onUploadStart();
      const response = await uploadVideo(payload);
      onUploadComplete(response);
      setFile(null);
      setVideoPath('');
      (event.target as HTMLFormElement).reset();
    } catch (error: any) {
      const message = error?.response?.data?.detail ?? error?.message ?? 'Upload failed';
      onError(message);
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="card">
      <h2 className="section-title">Upload CCTV Footage</h2>
      <form onSubmit={handleSubmit} className="upload-grid">
        <div className="input-group">
          <label htmlFor="videoFile">Video File</label>
          <input
            id="videoFile"
            type="file"
            accept="video/mp4,video/x-matroska,video/avi"
            onChange={(e) => setFile(e.target.files?.[0] ?? null)}
          />
          <small>Optionally upload a CCTV recording directly.</small>
        </div>

        <div className="input-group">
          <label htmlFor="videoPath">Existing Server Path</label>
          <input
            id="videoPath"
            type="text"
            placeholder="/path/to/cctv.mp4"
            value={videoPath}
            onChange={(e) => setVideoPath(e.target.value)}
          />
          <small>Provide a path to an existing video accessible by the backend.</small>
        </div>

        <div className="input-group" style={{ alignSelf: 'flex-end' }}>
          <button className="primary-button" type="submit" disabled={isSubmitting}>
            {isSubmitting ? 'Processing…' : 'Process Footage'}
          </button>
        </div>
      </form>
    </div>
  );
}
