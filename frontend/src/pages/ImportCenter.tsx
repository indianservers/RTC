import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useSearchParams } from "react-router-dom";
import { api, post, errorText, type Row } from "../api";
import { FarePreview } from "./FarePreview";
import { Badge, Button, Notice } from "../components/ui";
import { ConfirmDialog, LoadingSkeleton } from "../components/feedback";

export function ImportCenter({
  token,
  resources,
  role,
}: {
  token: string;
  resources: Row;
  role: string;
}) {
  const headers = { Authorization: `Bearer ${token}` };
  const [params, setParams] = useSearchParams();
  const [resource, setResource] = useState("stations");
  const [file, setFile] = useState<File>();
  const [batch, setBatch] = useState<Row>();
  const [mapping, setMapping] = useState<Record<string, string>>({});
  const [mode, setMode] = useState("insert_only");
  const [offset, setOffset] = useState(0);
  const [pending, setPending] = useState("");
  const [error, setError] = useState("");
  const client = useQueryClient();
  const list = useQuery({
    queryKey: ["data-batches", token, offset],
    queryFn: ({ signal }) =>
      api(`/admin/imports/batches?offset=${offset}&limit=20`, {
        headers,
        signal,
      }),
  });
  const selected = params.get("batch");
  const details = useQuery({
    queryKey: ["data-batch", selected, token],
    queryFn: () => api(`/admin/imports/batches/${selected}`, { headers }),
    enabled: !!selected,
  });
  const current = batch?.id === selected ? batch : details.data?.data;
  const schema = useQuery({
    queryKey: ["import-template", resource, token],
    queryFn: () => api(`/admin/data/templates/${resource}`, { headers }),
  });
  function show(row: Row) {
    setBatch(row);
    setParams({ batch: row.id });
    setMapping(row.mapping || {});
    setError("");
  }
  const upload = useMutation({
    mutationFn: async () => {
      if (!file) throw new Error("Choose a CSV or XLSX file.");
      if (file.size > 10000000) throw new Error("Maximum file size is 10 MB.");
      const bytes = new Uint8Array(await file.arrayBuffer());
      let binary = "";
      for (let i = 0; i < bytes.length; i += 32768)
        binary += String.fromCharCode(...bytes.subarray(i, i + 32768));
      return post(
        `/admin/imports/files/${resource}`,
        {
          filename: file.name,
          content_base64: btoa(binary),
          operator_id: sessionStorage.getItem("rtc-admin-operator") || null,
          source_id: sessionStorage.getItem("rtc-admin-source") || null,
          mode,
        },
        token,
      );
    },
    onSuccess: (r) => {
      show(r.data);
      void client.invalidateQueries({ queryKey: ["data-batches"] });
    },
    onError: (e) => setError(errorText(e)),
  });
  const action = useMutation({
    mutationFn: async (verb: string) => {
      if (!current) throw new Error("Choose a change set.");
      return post(
        `/admin/imports/batches/${current.id}/${verb}`,
        {
          revision: current.revision,
          reason: "Reviewed in local Import Center",
        },
        token,
      );
    },
    onSuccess: (r) => {
      show(r.data);
      void client.invalidateQueries();
    },
    onError: (e) => setError(errorText(e)),
  });
  const map = useMutation({
    mutationFn: () =>
      api(`/admin/imports/batches/${current.id}/mapping`, {
        method: "PUT",
        headers,
        body: JSON.stringify({
          revision: current.revision,
          mapping: Object.keys(mapping).length ? mapping : current.mapping,
          mode,
        }),
      }),
    onSuccess: (r) => show(r.data),
    onError: (e) => setError(errorText(e)),
  });
  const busy = upload.isPending || action.isPending || map.isPending;
  async function download(format: string) {
    try {
      const r = await fetch(
        `/api/v1/admin/data/templates/${resource}?format=${format}`,
        { headers },
      );
      if (!r.ok) throw new Error("Template download failed.");
      const url = URL.createObjectURL(await r.blob());
      const link = document.createElement("a");
      link.href = url;
      link.download = `FICTIONAL-template-${resource}.${format}`;
      link.click();
      URL.revokeObjectURL(url);
    } catch (e) {
      setError(errorText(e));
    }
  }
  return (
    <section className="panel import-center" aria-label="Staged Import Center">
      <div className="card-top">
        <div>
          <h2>Import Center</h2>
          <p>
            Upload → map → validate → review → approve → publish → verify.
            Drafts never change passenger answers.
          </p>
        </div>
        <Badge>Local files only</Badge>
      </div>
      <div className="edit-grid">
        <label className="field">
          Import resource
          <select
            value={resource}
            onChange={(e) => setResource(e.target.value)}
          >
            {Object.keys(resources)
              .filter((r) => !r.startsWith("nlp-"))
              .map((r) => (
                <option key={r}>{r}</option>
              ))}
          </select>
        </label>
        <label className="field">
          Write mode
          <select value={mode} onChange={(e) => setMode(e.target.value)}>
            <option value="insert_only">Insert new records only</option>
            <option value="update">Explicit updates using record_id</option>
          </select>
        </label>
        <label className="field">
          CSV or XLSX file (10 MB / 10,000 rows)
          <input
            type="file"
            accept=".csv,.xlsx"
            onChange={(e) => {
              setFile(e.target.files?.[0]);
              setError("");
            }}
          />
        </label>
      </div>
      <div className="card-actions">
        <Button
          disabled={busy || !file || role === "APPROVER"}
          onClick={() => upload.mutate()}
        >
          Upload draft
        </Button>
        <Button variant="secondary" onClick={() => void download("csv")}>
          Download CSV template
        </Button>
        <Button variant="ghost" onClick={() => void download("json")}>
          Schema & validation rules
        </Button>
      </div>
      {schema.data && (
        <p className="subtle">
          Required: {schema.data.data.required_columns.join(", ")}. Templates
          contain fictional formatting examples. Reference IDs must come from
          this database.
        </p>
      )}
      {error && <Notice error>{error}</Notice>}
      {details.isPending && selected && (
        <LoadingSkeleton label="Opening change set…" />
      )}
      {current && (
        <section aria-label="Change set review" className="comparison-panel">
          <div className="card-top">
            <h3>Change set {current.id}</h3>
            <Badge>{current.workflow_state}</Badge>
          </div>
          <p>
            {current.row_count} rows · revision {current.revision} · creator{" "}
            {current.uploaded_by || "Legacy"} · approver{" "}
            {current.approved_by || "Not approved"}
          </p>
          <p className="subtle">
            Source checksum: {current.source_checksum || "Not recorded"}.
            Published by {current.published_by || "Not published"}.
          </p>
          {current.headers?.length > 0 &&
            ["DRAFT", "VALIDATED"].includes(current.workflow_state) && (
              <details open>
                <summary>Map input columns</summary>
                <div className="edit-grid">
                  {current.headers.map((h: string) => (
                    <label key={h} className="field">
                      {h}
                      <select
                        aria-label={`Map ${h}`}
                        value={mapping[h] ?? current.mapping?.[h] ?? ""}
                        onChange={(e) =>
                          setMapping((m) => ({
                            ...current.mapping,
                            ...m,
                            [h]: e.target.value,
                          }))
                        }
                      >
                        <option value="">Explicitly ignore column</option>
                        <option value="record_id">
                          record_id (update only)
                        </option>
                        {Object.keys(
                          resources[current.resource]?.schema.properties || {},
                        ).map((k) => (
                          <option key={k}>{k}</option>
                        ))}
                      </select>
                    </label>
                  ))}
                </div>
                <Button
                  variant="secondary"
                  disabled={busy || role === "APPROVER"}
                  onClick={() => map.mutate()}
                >
                  Save column mapping
                </Button>
              </details>
            )}
          {current.validation_report && (
            <>
              <Notice error={current.validation_report.errors.length > 0}>
                {current.validation_report.errors.length
                  ? `${current.validation_report.errors.length} validation error(s). Nothing can publish.`
                  : `${current.validation_report.valid_rows} validated row(s). No live data changed during validation.`}
              </Notice>
              {current.validation_report.errors.map((e: Row, i: number) => (
                <p key={i} role="alert">
                  {e.severity} · row {e.row ?? "batch"}: {e.message}
                </p>
              ))}
              <details>
                <summary>Before / after preview (first 100 changes)</summary>
                <pre className="debug-output">
                  {JSON.stringify(current.validation_report.preview, null, 2)}
                </pre>
              </details>
            </>
          )}
          {["VALIDATED", "APPROVED"].includes(current.workflow_state) &&
            ["fares", "fare-rules", "trip-fare-overrides", "bundle"].includes(
              current.resource,
            ) && <FarePreview token={token} batchId={current.id} />}
          <div className="card-actions">
            {["DRAFT", "VALIDATED"].includes(current.workflow_state) && (
              <Button
                disabled={busy || role === "APPROVER"}
                onClick={() => action.mutate("validate")}
              >
                Validate change set
              </Button>
            )}
            {current.workflow_state === "VALIDATED" && (
              <Button
                disabled={busy || role === "EDITOR"}
                onClick={() => setPending("approve")}
              >
                Approve change set
              </Button>
            )}
            {current.workflow_state === "APPROVED" && (
              <Button
                disabled={busy || role === "EDITOR"}
                onClick={() => setPending("publish")}
              >
                Publish approved changes
              </Button>
            )}
            {current.workflow_state === "PUBLISHED" && (
              <Button
                variant="secondary"
                disabled={
                  busy || role === "EDITOR" || !current.rollback_eligible
                }
                onClick={() => setPending("rollback")}
              >
                Request safe rollback
              </Button>
            )}
            <Button
              variant="ghost"
              disabled={busy}
              onClick={() => {
                setBatch(undefined);
                void details.refetch();
              }}
            >
              Refresh verification
            </Button>
          </div>
          {current.workflow_state === "PUBLISHED" &&
            !current.rollback_eligible && (
              <Notice>
                Legacy batch: reversible before/after snapshots were not
                recorded. Automatic rollback is unavailable.
              </Notice>
            )}
          <p className="subtle">
            Approval requires a different authorized user. Newer edits or
            dependent records can block rollback. Publication and rollback are
            atomic.
          </p>
        </section>
      )}
      <ConfirmDialog
        open={!!pending}
        onOpenChange={(open) => {
          if (!open) setPending("");
        }}
        title={`${pending} change set?`}
        description="The backend checks role, operator, independent approval, revision and current record values. Live data changes only after a valid publish or rollback."
        onConfirm={() => action.mutate(pending)}
        pending={busy}
      />
      <h3>Stored import and change history</h3>
      {list.error && <Notice error>{errorText(list.error)}</Notice>}
      <div className="table-scroll">
        <table>
          <thead>
            <tr>
              <th>Source/resource</th>
              <th>State</th>
              <th>Rows</th>
              <th>Created</th>
              <th>Review</th>
            </tr>
          </thead>
          <tbody>
            {list.data?.data.map((b: Row) => (
              <tr key={b.id}>
                <td>{b.source_filename || b.resource}</td>
                <td>{b.workflow_state}</td>
                <td>{b.row_count}</td>
                <td>{b.created_at || "Legacy timestamp unavailable"}</td>
                <td>
                  <Button
                    variant="ghost"
                    onClick={() => {
                      setBatch(undefined);
                      setMapping({});
                      setParams({ batch: b.id });
                    }}
                  >
                    Review change set
                  </Button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <div className="pagination">
        <span>{list.data?.total ?? 0} stored batches</span>
        <Button
          variant="ghost"
          disabled={!offset}
          onClick={() => setOffset((n) => Math.max(0, n - 20))}
        >
          Previous batches
        </Button>
        <Button
          variant="ghost"
          disabled={offset + 20 >= (list.data?.total || 0)}
          onClick={() => setOffset((n) => n + 20)}
        >
          Next batches
        </Button>
      </div>
    </section>
  );
}
