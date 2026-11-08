import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { api, errorText, type Row } from "../api";
import { Button, Notice } from "../components/ui";
import { RecordDrawer } from "../components/feedback";
export function AuditHistory({ token }: { token: string }) {
  const [offset, setOffset] = useState(0);
  const [entity, setEntity] = useState("");
  const [filter, setFilter] = useState("");
  const [detail, setDetail] = useState<Row | null>(null);
  const data = useQuery({
    queryKey: ["audit-history", token, offset, filter],
    queryFn: ({ signal }) =>
      api(
        `/admin/data/audit?limit=25&offset=${offset}${filter ? `&entity_id=${encodeURIComponent(filter)}` : ""}`,
        { signal, headers: { Authorization: `Bearer ${token}` } },
      ),
  });
  return (
    <section className="panel">
      <h2>Audit history</h2>
      <p>
        Immutable local before/after history. Rollbacks create new audit
        versions.
      </p>
      <form
        className="filter-bar"
        onSubmit={(e) => {
          e.preventDefault();
          setFilter(entity);
          setOffset(0);
        }}
      >
        <label className="field">
          Record ID
          <input value={entity} onChange={(e) => setEntity(e.target.value)} />
        </label>
        <Button>Find audit records</Button>
      </form>
      {data.error && <Notice error>{errorText(data.error)}</Notice>}
      <RecordDrawer
        record={detail}
        onClose={() => setDetail(null)}
        title="Audit event"
      />
      <div className="table-scroll">
        <table>
          <thead>
            <tr>
              <th>Time</th>
              <th>Actor</th>
              <th>Resource / record</th>
              <th>Operation</th>
              <th>Version</th>
              <th>Values</th>
            </tr>
          </thead>
          <tbody>
            {data.data?.data.map((row: Row) => (
              <tr key={row.id}>
                <td>{row.recorded_at}</td>
                <td>{row.actor}</td>
                <td>
                  {row.entity_type}
                  <br />
                  {row.entity_id}
                </td>
                <td>{row.operation}</td>
                <td>{row.version ?? "Workflow event"}</td>
                <td>
                  <Button variant="ghost" onClick={() => setDetail(row)}>
                    View audit values
                  </Button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <div className="pagination">
        <span>{data.data?.total ?? 0} matching audit events</span>
        <Button
          variant="ghost"
          disabled={!offset}
          onClick={() => setOffset((n) => Math.max(0, n - 25))}
        >
          Previous audit events
        </Button>
        <Button
          variant="ghost"
          disabled={offset + 25 >= (data.data?.total || 0)}
          onClick={() => setOffset((n) => n + 25)}
        >
          Next audit events
        </Button>
      </div>
    </section>
  );
}
