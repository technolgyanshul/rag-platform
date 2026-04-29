import { Source } from "../../lib/types";

type SourceListProps = {
  sources: Source[];
};

export function SourceList({ sources }: SourceListProps) {
  if (sources.length === 0) {
    return <p className="status-message">No sources available for this answer.</p>;
  }

  return (
    <ul className="source-list">
      {sources.map((source, index) => (
        <li key={`${source.document_id}-${source.chunk_index}-${index}`} className="source-item">
          <p>
            <strong>{source.filename}</strong>#{source.chunk_index} (score: {source.score.toFixed(3)})
          </p>
          <p>{source.content_preview}</p>
        </li>
      ))}
    </ul>
  );
}
