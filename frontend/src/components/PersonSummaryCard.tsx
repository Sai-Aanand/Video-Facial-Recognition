import type { PersonSummary } from '../types';

interface Props {
  person: PersonSummary;
}

export default function PersonSummaryCard({ person }: Props) {
  return (
    <div className="person-card">
      <div className="person-header">
        <strong>{person.name}</strong>
        <span className="status-pill completed">{person.appearances} sightings</span>
      </div>
      <table className="appearance-table">
        <thead>
          <tr>
            <th>Timestamp (s)</th>
            <th>Frame</th>
            <th>Bounding Box</th>
          </tr>
        </thead>
        <tbody>
          {person.details.map((detail, index) => (
            <tr key={`${person.person_id}-${index}`}>
              <td>{detail.timestamp.toFixed(2)}</td>
              <td>{detail.frame_index}</td>
              <td>{detail.bounding_box.join(', ')}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
