import { useEffect, useMemo, useState } from 'react';
import UploadPanel from './components/UploadPanel';
import VideoResultCard from './components/VideoResultCard';
import VideoHistoryList from './components/VideoHistoryList';
import { getVideo, listVideos } from './api/client';
import type { UploadResponse, VideoRecord } from './types';

export default function App() {
  const [videos, setVideos] = useState<VideoRecord[]>([]);
  const [selectedVideoId, setSelectedVideoId] = useState<string | null>(null);
  const [activeVideo, setActiveVideo] = useState<VideoRecord | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);

  useEffect(() => {
    const loadVideos = async () => {
      setIsLoading(true);
      try {
        const data = await listVideos();
        setVideos(data);
        if (data.length > 0 && !selectedVideoId) {
          setSelectedVideoId(data[0].video_id);
          setActiveVideo(data[0]);
        }
      } catch (err: any) {
        setError(err?.message ?? 'Failed to load videos');
      } finally {
        setIsLoading(false);
      }
    };

    loadVideos();
  }, []);

  useEffect(() => {
    if (!selectedVideoId) {
      setActiveVideo(null);
      return;
    }

    let cancelled = false;
    let pollTimer: ReturnType<typeof setInterval> | null = null;

    const fetchVideo = async () => {
      try {
        const detailed = await getVideo(selectedVideoId);
        if (cancelled) {
          return;
        }

        setError(null);
        setActiveVideo(detailed);
        setVideos((prev) => {
          const found = prev.some((item) => item.video_id === detailed.video_id);
          if (!found) {
            return [detailed, ...prev];
          }
          return prev.map((item) => (item.video_id === detailed.video_id ? detailed : item));
        });

        const shouldContinue = ['processing', 'processed'].includes(detailed.status);
        if (!shouldContinue && pollTimer) {
          clearInterval(pollTimer);
          pollTimer = null;
        }
      } catch (err: any) {
        if (!cancelled) {
          setError(err?.message ?? 'Unable to fetch video details');
        }
      }
    };

    fetchVideo();
    pollTimer = setInterval(fetchVideo, 2500);

    return () => {
      cancelled = true;
      if (pollTimer) {
        clearInterval(pollTimer);
      }
    };
  }, [selectedVideoId]);

  const handleUploadComplete = (result: UploadResponse) => {
    setError(null);
    setVideos((prev) => [result, ...prev.filter((item) => item.video_id !== result.video_id)]);
    setSelectedVideoId(result.video_id);
    setActiveVideo(result);
  };

  const handleUploadStart = () => {
    setError(null);
  };

  const handleError = (message: string) => {
    setError(message);
  };

  const handleSelectVideo = (videoId: string) => {
    setSelectedVideoId(videoId);
  };

  const sortedVideos = useMemo(
    () => [...videos].sort((a, b) => (a.created_at < b.created_at ? 1 : -1)),
    [videos]
  );

  return (
    <div className="app-container">
      <h1 style={{ marginBottom: 24 }}>Facial Recognition Dashboard</h1>
      <UploadPanel onUploadComplete={handleUploadComplete} onUploadStart={handleUploadStart} onError={handleError} />

      {error && (
        <div className="card" style={{ border: '1px solid #fecaca' }}>
          <strong className="error-text">{error}</strong>
        </div>
      )}

      {activeVideo && <VideoResultCard video={activeVideo} />}

      <VideoHistoryList videos={sortedVideos} onSelect={handleSelectVideo} />

      {isLoading && <small>Loading videos…</small>}
    </div>
  );
}
