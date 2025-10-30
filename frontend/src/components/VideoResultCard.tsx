import type { VideoRecord } from '../types';
import PersonSummaryCard from './PersonSummaryCard';

interface Props {
  video: VideoRecord;
}

export default function VideoResultCard({ video }: Props) {
  const { summary } = video;
  const statusClass = `status-pill ${video.status}`;
  const statusLabel = `${video.status.charAt(0).toUpperCase()}${video.status.slice(1)}`;
  const processingSeconds = video.processing_time_seconds ?? null;
  const rawProgress = video.processing_progress ?? null;
  const normalizedProgress = rawProgress !== null ? Math.max(0, Math.min(100, rawProgress)) : null;
  const isInProgress = video.status === 'processing' || video.status === 'processed';

  const formatProcessingTime = (seconds: number) => {
    if (seconds < 60) {
      return `${seconds.toFixed(1)} s`;
    }
    const minutes = Math.floor(seconds / 60);
    const remaining = seconds % 60;
    return `${minutes}m ${remaining.toFixed(0)}s`;
  };

  return (
    <div className="card">
      <div className="person-header">
        <h3>{video.filename}</h3>
        <span className={statusClass}>{statusLabel}</span>
      </div>
      <small>Processed on {new Date(video.created_at).toLocaleString()}</small>

      <div className="summary-grid" style={{ marginTop: 16 }}>
        <div className="summary-tile">
          <strong>{summary.unique_people}</strong>
          <span>Unique People</span>
        </div>
        <div className="summary-tile">
          <strong>{summary.total_faces}</strong>
          <span>Total Appearances</span>
        </div>
        <div className="summary-tile">
          <strong>{processingSeconds !== null ? formatProcessingTime(processingSeconds) : '—'}</strong>
          <span>Processing Time</span>
        </div>
      </div>

      {isInProgress && (
        <div className="progress-section">
          <div className="progress-container">
            <div className="progress-bar" style={{ width: `${normalizedProgress ?? 0}%` }} />
          </div>
          <small className="progress-label">
            {normalizedProgress !== null ? `Processing… ${normalizedProgress.toFixed(0)}%` : 'Processing…'}
          </small>
        </div>
      )}

      <div className="video-actions">
        {video.annotated_video_url && (
          <a className="secondary-button" href={video.annotated_video_url} target="_blank" rel="noreferrer">
            Download Annotated Video
          </a>
        )}
        {video.report_url && (
          <a className="secondary-button" href={video.report_url} target="_blank" rel="noreferrer">
            Download PDF Report
          </a>
        )}
      </div>

      {video.status === 'failed' && (
        <div className="error-text" style={{ marginTop: 12 }}>
          Processing failed. Check the backend logs for details.
        </div>
      )}

      <div style={{ marginTop: 24, display: 'grid', gap: 16 }}>
        {summary.per_person.map((person) => (
          <PersonSummaryCard key={person.person_id} person={person} />
        ))}
        {summary.per_person.length === 0 && <small>No faces detected.</small>}
      </div>
    </div>
  );
}
