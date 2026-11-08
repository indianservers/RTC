import { useQuery } from "@tanstack/react-query";
import { useWorkspace } from "../App";
import { api, type Row } from "../api";
import { Badge, Notice, Button } from "../components/ui";
import { ErrorState, LoadingSkeleton } from "../components/feedback";
export function SystemStatus({
  token,
  modelsOnly = false,
}: {
  token: string;
  modelsOnly?: boolean;
}) {
  const { bootstrap } = useWorkspace();
  const health = useQuery({
    queryKey: ["health"],
    queryFn: ({ signal }) => api("/nlp/health", { signal }),
    staleTime: 0,
    refetchInterval: 15000,
  });
  const models = useQuery({
    queryKey: ["admin-model-status", token],
    queryFn: ({ signal }) => api("/models/status", { signal }),
    staleTime: 0,
  });
  const quality = useQuery({
    queryKey: ["admin-status-quality", token],
    queryFn: ({ signal }) =>
      api("/admin/ui/data-quality?limit=1", {
        signal,
        headers: { Authorization: `Bearer ${token}` },
      }),
    staleTime: 0,
    refetchInterval: 30000,
  });
  const stale = quality.data?.data.checks
    .filter((c: Row) => c.code.startsWith("STALE_"))
    .reduce((n: number, c: Row) => n + c.count, 0);
  return (
    <section className="panel">
      <div className="card-top">
        <h3>{modelsOnly ? "Local model registry" : "Actual system state"}</h3>
        <Button
          variant="secondary"
          onClick={() => {
            void health.refetch();
            void models.refetch();
            void quality.refetch();
          }}
        >
          Refresh status
        </Button>
      </div>
      {health.isPending && <LoadingSkeleton />}
      {health.error && (
        <ErrorState
          message={health.error.message}
          onRetry={() => void health.refetch()}
        />
      )}
      <dl className="system-grid">
        <dt>Backend connection</dt>
        <dd>
          {health.isError
            ? "Backend unavailable"
            : health.isSuccess
              ? "Local backend connected"
              : "Checking"}
        </dd>
        {Object.entries(health.data?.data || {}).map(([k, v]) => (
          <div key={k}>
            <dt>{k.replaceAll("_", " ")}</dt>
            <dd>
              <Badge>{v == null ? "Not reported" : String(v)}</Badge>
            </dd>
          </div>
        ))}
        <dt>Active classifier</dt>
        <dd>
          {health.data?.data.statistical_model === "ACTIVE"
            ? health.data.data.active_model_name ||
              "Approved statistical model (name not reported)"
            : "Deterministic local rules; trained model not approved"}
        </dd>
        <dt>Local inventory</dt>
        <dd>
          {bootstrap?.counts.operators ?? "Unknown"} operators ·{" "}
          {bootstrap?.counts.stations ?? "Unknown"} stations ·{" "}
          {bootstrap?.counts.services ?? "Unknown"} services
        </dd>
        <dt>Data sources</dt>
        <dd>{bootstrap?.sources.join(", ") || "Not recorded"}</dd>
        <dt>Stale operational findings</dt>
        <dd>{stale === undefined ? "Not available" : stale}</dd>
        <dt>Dataset version / last import</dt>
        <dd>Not recorded by the current database schema</dd>
      </dl>
      {models.error && <ErrorState message={models.error.message} />}
      <div className="model-list">
        {models.data?.data.models?.map((m: Row) => (
          <article
            key={m.name || m.model_name || m.local_path}
            className="model-item"
          >
            <strong>
              {m.name || m.model_name || "Registered local model"}
            </strong>
            <p>
              Version: {m.version || "Not recorded"} · Download:{" "}
              {m.download_status || "Not reported"} · Verification:{" "}
              {String(
                m.load_verification_status ?? m.load_verified ?? "Not reported",
              )}
            </p>
          </article>
        ))}
      </div>
      <Notice>
        The browser's online flag is not offline certification. This app uses
        local assets/APIs; application-level blocked-egress tests are recorded
        in the report. OS-level isolation remains unverified.
      </Notice>
    </section>
  );
}
