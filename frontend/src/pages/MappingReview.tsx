import { Navigate, useParams } from "react-router-dom";

export function MappingReview() {
  const { id, mappingId } = useParams<{ id: string; mappingId: string }>();
  if (!id) {
    return <div className="p-6">Missing source ID.</div>;
  }
  const destination = mappingId ? `/sources/${id}/mapping?draft=${encodeURIComponent(mappingId)}` : `/sources/${id}/mapping`;
  return <Navigate to={destination} replace />;
}
