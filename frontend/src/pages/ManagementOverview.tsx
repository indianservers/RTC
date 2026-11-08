import { useState } from "react";
import { useQuery, useMutation } from "@tanstack/react-query";
import { api, post, errorText, type Row } from "../api";
import { Badge, Button, Notice } from "../components/ui";
export function ManagementOverview({ token }: { token: string }) {
  const [onboarding, setOnboarding] = useState("");
  const setup = useMutation({
    mutationFn: () => post("/admin/data/apsrtc-configuration", {}, token),
    onSuccess: (r) => setOnboarding(r.data.id),
  });
  const query = useQuery({
    queryKey: ["management-overview", token],
    queryFn: ({ signal }) =>
      api("/admin/data/overview", {
        signal,
        headers: { Authorization: `Bearer ${token}` },
      }),
  });
  const quality = useQuery({
    queryKey: ["management-quality", token],
    queryFn: ({ signal }) =>
      api("/admin/ui/data-quality?limit=1", {
        signal,
        headers: { Authorization: `Bearer ${token}` },
      }),
  });
  if (query.error) return <Notice error>{errorText(query.error)}</Notice>;
  const d = query.data?.data;
  return (
    <section className="panel">
      <h2>Operational data overview</h2>
      <p>
        Counts use active records in the selected authorization scope. Draft
        changes remain separate from passenger data.
      </p>
      <div className="system-grid">
        {[
          "stations",
          "routes",
          "schedules",
          "fares",
          "trips",
          "station-aliases",
        ].map((resource) => (
          <div className="panel" key={resource}>
            <small>{resource}</small>
            <h3>{d?.counts[resource] ?? "Checking local database…"}</h3>
          </div>
        ))}
      </div>
      {d?.role === "ADMIN" && (
        <>
          <Button
            variant="secondary"
            disabled={setup.isPending}
            onClick={() => setup.mutate()}
          >
            Stage APSRTC configuration
          </Button>
          <p className="subtle">
            Stages only the operator and branded category names requested for
            this project. Facilities stay unknown; no operational data is
            generated.
          </p>
          {setup.error && <Notice error>{errorText(setup.error)}</Notice>}
          {onboarding && (
            <Notice>
              APSRTC configuration is unpublished.{" "}
              <a href={`/admin/imports?batch=${onboarding}`}>
                Validate and obtain independent review
              </a>
            </Notice>
          )}
        </>
      )}
      <h3>Publication queue</h3>
      <div className="card-actions">
        {Object.entries(d?.workflow_counts || {}).map(([state, count]) => (
          <Badge key={state}>
            {state}: {String(count)}
          </Badge>
        ))}
      </div>
      <h3>Actual data-quality findings</h3>
      <ul>
        {quality.data?.data.checks.map((check: Row) => (
          <li key={check.code}>
            {check.label}: <strong>{check.count}</strong> ·{" "}
            {check.enterprise_severity || check.severity}
          </li>
        ))}
      </ul>
      <a href="/admin/data-quality">Review affected records and corrections</a>
      <Notice>
        Neither an import nor a validation run establishes official provenance.
        Use reviewed local sources and independent publication approval.
        Fictional examples remain DEMO.
      </Notice>
    </section>
  );
}
