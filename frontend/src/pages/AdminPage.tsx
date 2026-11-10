import { useState } from "react";
import { NavLink, useLocation } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import {
  ShieldCheck,
  LockKeyhole,
  LogOut,
  Upload,
  ArrowRight,
} from "lucide-react";

import { api, post, errorText, type Row, type Conversation } from "../api";
import { NlpReview } from "./NlpReview";
import { ManagementOverview } from "./ManagementOverview";
import { AccessManagement } from "./AccessManagement";
import { FarePreview } from "./FarePreview";
import { ImportCenter } from "./ImportCenter";
import { AuditHistory } from "./AuditHistory";
import { ManagementScope } from "./ManagementScope";
import { RouteEditor } from "./RouteEditor";
import { TimetableEditor } from "./TimetableEditor";
import { OperationsCenter } from "./OperationsCenter";
import { AdminTable } from "../components/AdminTable";
import { DataQualityPage } from "./DataQualityPage";
import { SystemStatus } from "./SystemStatus";
import { ConfirmDialog } from "../components/feedback";
import { useSearchParams } from "react-router-dom";
import { Badge, Button, Notice, PageTitle } from "../components/ui";
const simpleSections = [
  ["overview", "Start here"],
  ["stations", "1. Bus stations"],
  ["routes", "2. Routes"],
  ["route-editor", "3. Stops on a route"],
  ["schedules", "4. Bus services"],
  ["calendars", "5. Running days"],
  ["timetable-editor", "6. Arrival & departure times"],
  ["fares", "7. Ticket fares"],
  ["imports", "Review & publish / import"],
];
const guidance: Record<string, string> = {
  stations: "Add the places where buses stop. Reuse an existing station when it is already listed.",
  routes: "Add a route, then open Stops on a route to put its stations in travel order.",
  "route-editor": "Choose a route and arrange its stops from the first station to the last.",
  schedules: "Add a bus service: choose its operator, route, bus category and departure time.",
  calendars: "Choose when a service runs: its start and end dates and the days of the week.",
  "timetable-editor": "Choose an existing service, then enter the time at each stop.",
  fares: "Add the ticket price between stations for a bus service.",
};
const sections = [
  ["overview", "Overview"],
  ["operations", "Operations Control Center"],
  ["operators", "RTC Operators"],
  ["stations", "Stations"],
  ["station-aliases", "Station aliases"],
  ["bays", "Station bays"],
  ["depots", "Depots"],
  ["bus-types", "Bus Categories"],
  ["vehicle-types", "Vehicle characteristics"],
  ["vehicles", "Vehicles"],
  ["vehicle-assignments", "Vehicle assignments"],
  ["routes", "Routes"],
  ["route-editor", "Route & stop editor"],
  ["schedules", "Services"],
  ["calendars", "Service calendars"],
  ["timetable-editor", "Timetable editor"],
  ["stop-times", "Stop-wise times"],
  ["fares", "Fare Stages"],
  ["fare-rules", "Fare Rules"],
  ["fare-tables", "Fare tables"],
  ["concessions", "Concessions"],
  ["concession-eligibility", "Concession criteria"],
  ["trip-fare-overrides", "Trip fare overrides"],
  ["bus-type-aliases", "Bus type aliases"],
  ["platform-assignments", "Platform Assignments"],
  ["calendar-exceptions", "Service Exceptions"],
  ["imports", "Data Imports"],
  ["audit-history", "Audit History"],
  ["access", "Access & approvals"],
  ["route-variants", "Route variants"],
  ["variant-stops", "Variant stops"],
  ["quality-issues", "Issue resolution"],
  ["data-sources", "Data sources"],
  ["import-batches", "Import History"],
  ["diagnostics", "NLP Diagnostics"],
  ["nlp-review", "NLP Review Queue"],
  ["operational-events", "Operational Events"],
  ["data-quality", "Data Quality"],
  ["models", "Model Status"],
  ["status", "System Status"],
];
export function AdminPage() {
  const [advanced, setAdvanced] = useState(false);
  const [token, setToken] = useState("");
  const [draft, setDraft] = useState("");
  const client = useQueryClient();
  const location = useLocation();
  const section = location.pathname.split("/")[2] || "overview";

  const meta = useQuery({
    queryKey: ["admin-auth", token],
    queryFn: () =>
      api("/admin/ui/metadata", {
        headers: { Authorization: `Bearer ${token}` },
      }),
    enabled: !!token,
    retry: false,
    staleTime: 0,
    refetchInterval: 30000,
  });
  if (!meta.isSuccess)
    return (
      <div className="login-wrap">
        <section className="login panel">
          <span className="welcome-mark">
            <ShieldCheck size={30} />
          </span>
          <span className="eyebrow">LOCAL ADMINISTRATION</span>
          <h1>Administrator access</h1>
          <p>
            Use the administrator token configured on this local RTC backend.
          </p>
          <form
            onSubmit={(e) => {
              e.preventDefault();
              sessionStorage.removeItem("rtc-admin-operator");
              sessionStorage.removeItem("rtc-admin-source");
              setToken(draft);
            }}
          >
            <label className="field">
              Administrator token
              <input
                type="password"
                required
                value={draft}
                onChange={(e) => setDraft(e.target.value)}
                autoComplete="off"
              />
            </label>
            <Button disabled={meta.isFetching} type="submit">
              <LockKeyhole size={16} />
              {meta.isFetching ? "Verifying…" : "Unlock administration"}
              <ArrowRight size={16} />
            </Button>
          </form>
          {meta.error && <Notice error>{meta.error.message}</Notice>}
          <small>
            The token stays in memory. Mutations are authorized by the backend.
          </small>
        </section>
      </div>
    );
  const resources = meta.data.data.resources;
  const readonly = meta.data.data.readonly.includes(section);
  return (
    <div className="page-container admin-page">
      <PageTitle
        eyebrow="LOCAL CONTROL CENTRE"
        title="Add & manage bus information"
        description="Start with stations and routes, then add your bus services and timings."
        actions={
          <Button
            variant="secondary"
            onClick={() => {
              setToken("");
              setDraft("");
              client.removeQueries({
                predicate: (q) => String(q.queryKey[0]).startsWith("admin"),
              });
            }}
          >
            <LogOut size={15} />
            Lock admin
          </Button>
        }
      />
      <details className="panel">
        <summary>Operator & data source settings</summary>
        <ManagementScope token={token} meta={meta.data.data} />
      </details>
      {meta.data.data.publication_required && <Notice>Saved changes are drafts. Use Review & publish to validate them and obtain approval before passengers can see them.</Notice>}
      <Button variant="secondary" onClick={() => setAdvanced(!advanced)}>
        {advanced ? "Show simple menu" : "Show all administration tools"}
      </Button>
      <div className="admin-layout">
        <nav className="admin-nav" aria-label="Administration sections">
          {(advanced ? sections : simpleSections).map(([key, label]) => (
            <NavLink
              end
              key={key}
              to={key === "overview" ? "/admin" : `/admin/${key}`}
            >
              <span>{label}</span>
              {readonly && key === section && <small>View</small>}
            </NavLink>
          ))}
        </nav>
        <section className="admin-content">
          <h2>
            {(advanced ? sections : simpleSections).find((s) => s[0] === section)?.[1] || sections.find((s) => s[0] === section)?.[1] || "Administration"}
          </h2>
          {guidance[section] && <p>{guidance[section]} Use Add to enter a new record, or the pencil to change an existing one.</p>}
          {section === "overview" && (
            <section className="panel">
              <h3>What would you like to add?</h3>
              <p>For a new timetable, follow these steps in order. Skip anything already in your database.</p>
              <div className="system-grid">
                {simpleSections.slice(1, 8).map(([key, label]) => (
                  <NavLink className="panel" key={key} to={`/admin/${key}`}>
                    <strong>{label}</strong><p>{guidance[key]}</p>
                  </NavLink>
                ))}
              </div>
              <p>Need an operator or bus category first? Open all administration tools to add it.</p>
              <details><summary>Database overview & setup tools</summary><ManagementOverview token={token} /></details>
            </section>
          )}
          {[
            "fares",
            "fare-tables",
            "fare-rules",
            "concessions",
            "trip-fare-overrides",
          ].includes(section) && <FarePreview token={token} />}
          {section === "operations" ? (
            <OperationsCenter token={token} role={meta.data.data.role} />
          ) : section === "overview" ? (
            null
          ) : section === "imports" ? (
            <>
              <ImportCenter
                token={token}
                resources={resources}
                role={meta.data.data.role}
              />
              <details open={meta.data.data.demo_bypass}>
                <summary>Compatible CSV dry-run / demo tool</summary>
                <Imports token={token} resources={resources} />
              </details>
            </>
          ) : section === "audit-history" ? (
            <AuditHistory token={token} />
          ) : section === "access" ? (
            <AccessManagement token={token} role={meta.data.data.role} />
          ) : section === "route-editor" ? (
            meta.data.data.role === "APPROVER" ? (
              <Notice>
                Approver access is read-only. Use Import Center to review and
                approve changes.
              </Notice>
            ) : (
              <RouteEditor token={token} />
            )
          ) : section === "timetable-editor" ? (
            meta.data.data.role === "APPROVER" ? (
              <Notice>
                Approver access is read-only. Use Import Center to review and
                approve changes.
              </Notice>
            ) : (
              <TimetableEditor token={token} />
            )
          ) : section === "nlp-review" ? (
            <NlpReview token={token} />
          ) : section === "diagnostics" ? (
            <Diagnostics token={token} />
          ) : section === "data-quality" ? (
            <DataQualityPage token={token} />
          ) : section === "operational-events" ? (
            <OperationalEvents token={token} meta={meta.data.data} />
          ) : section === "status" || section === "models" ? (
            <SystemStatus token={token} modelsOnly={section === "models"} />
          ) : resources[section] || readonly ? (
            <AdminTable
              key={section}
              resource={section}
              token={token}
              definition={resources[section]}
              readonly={
                readonly ||
                !meta.data.data.permissions?.write_resources?.includes(section)
              }
            />
          ) : (
            <Notice>
              No supported management API is available for this section.
            </Notice>
          )}
        </section>
      </div>
    </div>
  );
}
function Imports({ token, resources }: { token: string; resources: Row }) {
  const [resource, setResource] = useState("stations");
  const [csv, setCsv] = useState("");
  const [dry, setDry] = useState(true);
  const [fileError, setFileError] = useState("");
  const [confirmImport, setConfirmImport] = useState(false);
  const upload = useMutation({
    mutationFn: () =>
      api(`/admin/imports/${resource}?dry_run=${dry}`, {
        method: "POST",
        headers: {
          Authorization: `Bearer ${token}`,
          "Content-Type": "text/csv",
        },
        body: csv,
      }),
  });
  return (
    <section className="panel">
      <p>
        Validate a local CSV before importing. Files commit atomically only when
        the backend reports success.
      </p>
      <label className="field">
        Resource
        <select
          value={resource}
          onChange={(e) => {
            setResource(e.target.value);
            upload.reset();
          }}
        >
          {Object.keys(resources).map((r) => (
            <option key={r}>{r}</option>
          ))}
        </select>
      </label>
      <p className="subtle">
        Columns:{" "}
        {Object.keys(resources[resource]?.schema.properties || {}).join(", ")}
      </p>
      <label className="field">
        CSV file (maximum 2 MB)
        <input
          type="file"
          accept=".csv,text/csv"
          onChange={async (e) => {
            const file = e.target.files?.[0];
            if (file) {
              if (file.size > 2000000) {
                setFileError("File exceeds 2 MB.");
                setCsv("");
                upload.reset();
                return;
              }
              setFileError("");
              setCsv(await file.text());
              upload.reset();
            }
          }}
        />
      </label>
      <label className="field">
        CSV content
        <textarea
          rows={6}
          value={csv}
          onChange={(e) => {
            setCsv(e.target.value);
            upload.reset();
          }}
        />
      </label>
      <label className="check-field">
        <input
          type="checkbox"
          checked={dry}
          onChange={(e) => setDry(e.target.checked)}
        />
        Dry-run validation (no data changes)
      </label>
      <Button
        disabled={!csv || upload.isPending}
        onClick={() => {
          if (dry) upload.mutate();
          else setConfirmImport(true);
        }}
      >
        <Upload size={15} />
        {upload.isPending ? "Validating…" : dry ? "Validate CSV" : "Import CSV"}
      </Button>
      {(fileError || upload.error) && (
        <Notice error>{fileError || errorText(upload.error)}</Notice>
      )}
      <ConfirmDialog
        open={confirmImport}
        onOpenChange={setConfirmImport}
        title="Import this CSV?"
        description="The backend validates all rows and commits atomically only when every row is valid."
        onConfirm={() => upload.mutate()}
        pending={upload.isPending}
      />
      {upload.data && (
        <Notice error={upload.data.data.errors.length > 0}>
          {upload.data.data.publication_state
            ? `Unpublished change set ${upload.data.data.batch_id}: ${upload.data.data.publication_state}. Continue in Import Center.`
            : upload.data.data.errors.length
              ? `Import validation failed: ${upload.data.data.errors.length} row error(s). No rows were committed.`
              : upload.data.data.committed
                ? `Import committed. ${upload.data.data.inserted} inserted; ${upload.data.data.duplicates} duplicate(s) skipped.`
                : `Dry run passed. ${upload.data.data.inserted} row(s) would be inserted; no data committed.`}
        </Notice>
      )}
      {upload.data && upload.data.data.errors.length > 0 && (
        <div className="table-scroll">
          <table>
            <thead>
              <tr>
                <th>CSV row</th>
                <th>Validation error</th>
              </tr>
            </thead>
            <tbody>
              {upload.data.data.errors.map((error: Row) => (
                <tr key={error.row}>
                  <td>{error.row}</td>
                  <td>{error.error}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      {upload.data && (
        <pre className="debug-output" aria-label="Import result">
          {JSON.stringify(upload.data.data, null, 2)}
        </pre>
      )}
    </section>
  );
}
function Diagnostics({ token }: { token: string }) {
  const [text, setText] = useState("");
  const run = useMutation({
    mutationFn: () =>
      post<Conversation>(
        "/admin/ui/diagnostics",
        { text, language: "en", debug: true },
        token,
      ),
  });
  return (
    <section className="panel">
      <Badge tone="amber">DEVELOPER ONLY</Badge>
      <p>
        Inspect deterministic rules and model readiness. Rule scores are not
        calibrated probabilities. This does not modify passenger sessions.
      </p>
      <form
        onSubmit={(e) => {
          e.preventDefault();
          run.mutate();
        }}
      >
        <label className="field">
          Passenger message
          <textarea
            required
            value={text}
            maxLength={2000}
            onChange={(e) => setText(e.target.value)}
          />
        </label>
        <Button disabled={run.isPending} type="submit">
          Run local diagnostics
        </Button>
      </form>
      {run.error && <Notice error>{errorText(run.error)}</Notice>}
      {run.data && (
        <>
          <dl className="diagnostic-grid">
            <dt>Input text</dt>
            <dd>{run.data.debug.input || text}</dd>
            <dt>Normalized text</dt>
            <dd>{run.data.debug.normalized_text || "Not reported"}</dd>
            <dt>Primary intent</dt>
            <dd>{run.data.intents[0] || "None"}</dd>
            <dt>Secondary intents</dt>
            <dd>{run.data.intents.slice(1).join(", ") || "None"}</dd>
            <dt>Classifier</dt>
            <dd>
              {run.data.debug.prediction?.status === "RULES"
                ? "Deterministic local rules"
                : run.data.debug.prediction?.model ||
                  run.data.debug.prediction?.status ||
                  "Not reported"}
            </dd>
            <dt>Model version</dt>
            <dd>{run.data.debug.prediction?.version || "Not reported"}</dd>
            <dt>Selected station / service</dt>
            <dd>
              {run.data.context.origin || "Not selected"} /{" "}
              {run.data.context.service_id || "Not selected"}
            </dd>
            <dt>Enquiry function</dt>
            <dd>{run.data.debug.database_function || "No enquiry invoked"}</dd>
            <dt>Result count</dt>
            <dd>
              {run.data.results.reduce(
                (n, r) => n + (r.results?.length || 0),
                0,
              )}
            </dd>
            <dt>Response template/route</dt>
            <dd>
              {run.data.debug.response_template?.join(", ") || "Not reported"}
            </dd>
            <dt>Intents</dt>
            <dd>{run.data.intents.join(", ") || "None"}</dd>
            <dt>Latency</dt>
            <dd>{run.data.duration_ms.toFixed(1)} ms</dd>
            <dt>Answer</dt>
            <dd>{run.data.answer}</dd>
            <dt>Confidence</dt>
            <dd>Not calibrated / not available</dd>
          </dl>
          <pre className="debug-output">
            {JSON.stringify(
              {
                original: text,
                entities: run.data.entities,
                context: run.data.context,
                changes: run.data.context_changes,
                results: run.data.results,
                debug: run.data.debug,
                warnings: run.data.warnings,
              },
              null,
              2,
            )}
          </pre>
        </>
      )}
    </section>
  );
}

function OperationalEvents({ token, meta }: { token: string; meta: Row }) {
  const [params, setParams] = useSearchParams();
  const allowed = [
    "trips",
    "delay-events",
    "stop-observations",
    "service-disruptions",
    "location-updates",
  ];
  const resource = allowed.includes(params.get("resource") || "")
    ? params.get("resource")!
    : "trips";
  return (
    <>
      <label className="field">
        Event domain
        <select
          value={resource}
          onChange={(e) => setParams({ resource: e.target.value })}
        >
          {allowed.map((value) => (
            <option key={value}>{value}</option>
          ))}
        </select>
      </label>
      <AdminTable
        key={resource + params.get("record")}
        resource={resource}
        token={token}
        definition={meta.resources?.[resource]}
        readonly={!meta.permissions?.write_resources?.includes(resource)}
      />
    </>
  );
}
