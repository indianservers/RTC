import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { api, today, type Row } from "../api";
import { FilterBar } from "../components/FilterBar";
import { Badge, Button, Notice } from "../components/ui";
import {
  ErrorState,
  LoadingSkeleton,
  RecordDrawer,
} from "../components/feedback";
export function DataQualityPage({ token }: { token: string }) {
  const [date, setDate] = useState(today());
  const [kind, setKind] = useState("");
  const [severity, setSeverity] = useState("");
  const [offset, setOffset] = useState(0);
  const [selected, setSelected] = useState<Row | null>(null);
  const query = useQuery({
    queryKey: ["admin-quality", token, date, kind, severity, offset],
    queryFn: ({ signal }) =>
      api(
        `/admin/ui/data-quality?audit_date=${date}&limit=25&offset=${offset}${kind ? `&kind=${kind}` : ""}${severity ? `&severity=${severity}` : ""}`,
        { signal, headers: { Authorization: `Bearer ${token}` } },
      ),
    staleTime: 0,
  });
  const d = query.data?.data;
  function recordLink(issue: Row) {
    if (issue.resource === "imports")
      return `/admin/imports?batch=${issue.batch_id || issue.record_id}`;
    const event = [
      "trips",
      "stop-observations",
      "delay-events",
      "location-updates",
      "service-disruptions",
    ].includes(issue.resource);
    return event
      ? `/admin/operational-events?resource=${issue.resource}&record=${issue.record_id}`
      : `/admin/${issue.resource}?record=${issue.batch_id || issue.record_id}`;
  }
  return (
    <>
      <p className="subtle">
        Read-only validation over actual local records. Findings describe
        coverage and validity, not invented operational conditions.
      </p>
      <FilterBar className="quality-filters" label="Data quality filters">
        <label className="field">
          Audit date
          <input
            type="date"
            value={date}
            onChange={(e) => {
              setDate(e.target.value);
              setOffset(0);
            }}
          />
        </label>
        <label className="field">
          Issue type
          <select
            value={kind}
            onChange={(e) => {
              setKind(e.target.value);
              setOffset(0);
            }}
          >
            <option value="">All checks</option>
            {d?.checks.map((c: Row) => (
              <option key={c.code} value={c.code}>
                {c.label} ({c.count})
              </option>
            ))}
          </select>
        </label>
        <label className="field">
          Severity
          <select
            value={severity}
            onChange={(e) => {
              setSeverity(e.target.value);
              setOffset(0);
            }}
          >
            <option value="">All severities</option>
            {["ERROR", "WARNING", "INFO"].map((v) => (
              <option key={v}>{v}</option>
            ))}
          </select>
        </label>
        <Button
          variant="secondary"
          disabled={query.isFetching}
          onClick={() => void query.refetch()}
        >
          Recheck database
        </Button>
      </FilterBar>
      {query.isPending && <LoadingSkeleton label="Auditing local records…" />}
      {query.error && (
        <ErrorState
          message={query.error.message}
          onRetry={() => void query.refetch()}
        />
      )}
      <div className="quality-summary">
        <strong>{d?.total ?? "—"}</strong>
        <span>
          matching findings
          {d?.as_of &&
            ` · Checked ${new Date(d.as_of).toLocaleString("en-IN")}`}
        </span>
      </div>
      <div className="quality-list">
        {d?.issues.map((issue: Row) => (
          <article className="panel quality-issue" key={issue.id}>
            <div className="card-top">
              <Badge tone={issue.severity === "ERROR" ? "amber" : "muted"}>
                {issue.severity}
              </Badge>
              <small>{issue.code}</small>
            </div>
            <h3>{issue.description}</h3>
            <p>{issue.suggested_correction}</p>
            <small>Record: {issue.record_id}</small>
            <div className="card-actions">
              <Link className="text-link" to={recordLink(issue)}>
                Open affected records
              </Link>
              <Button variant="ghost" onClick={() => setSelected(issue)}>
                Issue details
              </Button>
            </div>
          </article>
        ))}
      </div>
      {d && !d.issues.length && (
        <Notice>
          No matching findings from these checks. This is not certification that
          all data is complete.
        </Notice>
      )}
      {d && (
        <>
          <div className="pagination">
            <Button
              variant="secondary"
              disabled={!offset}
              onClick={() => setOffset((n) => n - 25)}
            >
              Previous findings
            </Button>
            <span>
              {Math.min(offset + 25, d.total)} of {d.total}
            </span>
            <Button
              variant="secondary"
              disabled={offset + 25 >= d.total}
              onClick={() => setOffset((n) => n + 25)}
            >
              Next findings
            </Button>
          </div>
          <details className="source-details">
            <summary>Check definitions and unavailable audits</summary>
            {d.notes.map((n: string) => (
              <p key={n}>{n}</p>
            ))}
            {d.unavailable_checks.map((c: Row) => (
              <p key={c.code}>
                <strong>{c.code} — Not available:</strong> {c.reason}
              </p>
            ))}
          </details>
        </>
      )}
      <RecordDrawer
        record={selected}
        title="Data quality finding"
        onClose={() => setSelected(null)}
      />
    </>
  );
}
