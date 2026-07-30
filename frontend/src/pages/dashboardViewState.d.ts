export function dashboardViewState(input: {
  loading: boolean;
  data: unknown;
  dashboardError: string;
}): "loading" | "initial_error" | "ready";
