import type { VideoRecord } from '../types';

interface Props {
  videos: VideoRecord[];
  onSelect: (videoId: string) => void;
}

export default function VideoHistoryList({ videos, onSelect }: Props) {
  const formatProcessingTime = (seconds?: number | null) => {
    if (seconds === null || seconds === undefined) {
      return 'Processing time: —';
    }
    if (seconds < 60) {
      return `Processing time: ${seconds.toFixed(1)} s`;
    }
    const minutes = Math.floor(seconds / 60);
    const remaining = seconds % 60;
    return `Processing time: ${minutes}m ${remaining.toFixed(0)}s`;
  };

  const formatStatus = (status: string) => `${status.charAt(0).toUpperCase()}${status.slice(1)}`;

  return (
    <div className="card">
      <h2 className="section-title">Processing History</h2>
      <ul className="activity-log">
        {videos.map((video) => (
          <li key={video.video_id} className="activity-item">
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <div>
                <strong>{video.filename}</strong>
                <br />
                <small>{new Date(video.created_at).toLocaleString()}</small>
                <br />
                <small>
                  {video.status === 'failed'
                    ? 'Processing failed'
                    : ['processing', 'processed'].includes(video.status)
                    ? `Progress: ${Math.round(video.processing_progress ?? 0)}%`
                    : formatProcessingTime(video.processing_time_seconds)}
                </small>
              </div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                <span className={`status-pill ${video.status}`}>{formatStatus(video.status)}</span>
                <button className="secondary-button" onClick={() => onSelect(video.video_id)}>
                  View Details
                </button>
              </div>
            </div>
          </li>
        ))}
        {videos.length === 0 && <small>No processed videos yet.</small>}
      </ul>
    </div>
  );
}
