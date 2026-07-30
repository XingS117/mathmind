export function dashboardViewState({ loading, data, dashboardError }) {
  if (loading && !data) return "loading";
  if (!data && dashboardError) return "initial_error";
  return "ready";
}
