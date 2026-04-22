import { Navigate, useParams } from "react-router-dom";

export function MappingReview() {
  const { id } = useParams<{ id: string }>();
  if (!id) {
    return <div className="p-6">Missing source ID.</div>;
  }
  return <Navigate to={`/sources/${id}/mapping`} replace />;
}
