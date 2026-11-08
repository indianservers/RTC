import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api, post, today, errorText, type Row, type Station } from "../api";
import { useWorkspace } from "../App";
import { useOperationsStream } from "../hooks/useOperationsStream";
import { StationPicker } from "../components/StationPicker";
import { Badge, Button, Notice } from "../components/ui";
import { ConfirmDialog } from "../components/feedback";

const actions = [
  "BOARDING",
  "READY",
  "ARRIVED_AT_STOP",
  "DEPARTED_FROM_STOP",
  "IN_TRANSIT",
  "COMPLETED",
  "DELAYED",
  "ETA",
  "PLATFORM",
  "CANCELLED",
  "SUSPENDED",
  "REINSTATE_REQUEST",
  "REINSTATE",
  "NOTICE_REQUEST",
  "PUBLISH_NOTICE",
  "ANNOUNCEMENT_REQUEST",
  "PUBLISH_ANNOUNCEMENT",
  "CORRECTION",
];
export function OperationsCenter({
  token = "",
  role = "OPERATIONS_VIEWER",
  passenger = false,
}: {
  token?: string;
  role?: string;
  passenger?: boolean;
}) {
  const workspace = useWorkspace();
  const [chosenStation, setStation] = useState<Station | undefined>(
    workspace.station,
  );
  const station = chosenStation || workspace.station;
  const [operator, setOperator] = useState(
    workspace.operator || sessionStorage.getItem("rtc-admin-operator") || "",
  );
  const [day, setDay] = useState(today());
  const [tab, setTab] = useState("departures");
  const [q, setQ] = useState("");
  const [category, setCategory] = useState("");
  const [offset, setOffset] = useState(0);
  const [sort, setSort] = useState("scheduled_departure");
  const [after, setAfter] = useState("");
  const [before, setBefore] = useState("");
  const [selected, setSelected] = useState<Row>();
  const [kind, setKind] = useState("DELAYED");
  const [source, setSource] = useState(
    sessionStorage.getItem("rtc-admin-source") || "",
  );
  const [reason, setReason] = useState("");
  const [bay, setBay] = useState("");
  const [delay, setDelay] = useState("15");
  const [eta, setEta] = useState("");
  const [estimateField, setEstimateField] = useState("estimated_departure");
  const [occurred, setOccurred] = useState("");
  const [expiryMinutes, setExpiryMinutes] = useState("60");
  const [target, setTarget] = useState("");
  const [corrected, setCorrected] = useState("ARRIVED_AT_STOP");
  const [disruptionType, setDisruptionType] = useState("SERVICE_INTERRUPTION");
  const [severity, setSeverity] = useState("HIGH");
  const [description, setDescription] = useState("");
  const [affected, setAffected] = useState("");
  const [affectedServices, setAffectedServices] = useState<string[]>([]);
  const [affectedRoutes, setAffectedRoutes] = useState<string[]>([]);
  const [affectedTrips, setAffectedTrips] = useState<string[]>([]);
  const [startsAt, setStartsAt] = useState("");
  const [endsAt, setEndsAt] = useState("");
  const [confirm, setConfirm] = useState(false);
  const [notice, setNotice] = useState("");
  const client = useQueryClient();
  const headers = { Authorization: `Bearer ${token}` };
  const connection = useOperationsStream(station?.id || "");
  const writable =
    !passenger &&
    role !== "OPERATIONS_VIEWER" &&
    ["ADMIN", "DISPATCHER", "STATION_SUPERVISOR", "OPERATOR_ADMIN"].includes(
      role,
    );
  const options = useQuery({
    queryKey: ["operations", "options"],
    queryFn: () => api("/app/bootstrap"),
  });
  const sources = useQuery({
    queryKey: ["operations", "sources", token, operator],
    queryFn: () =>
      api(
        `/admin/data-sources?limit=100${operator ? `&operator_id=${operator}` : ""}`,
        { headers },
      ),
    enabled: !!token,
  });
  const references = useQuery({
    queryKey: ["operations", "scope-references", operator, token],
    enabled: !!operator && !!token && !passenger,
    queryFn: async () => {
      const [services, routes, trips] = await Promise.all(
        ["schedules", "routes", "trips"].map((resource) =>
          api(
            `/admin/${resource}?operator_id=${encodeURIComponent(operator)}&limit=100`,
            { headers },
          ),
        ),
      );
      return {
        services: services.data,
        routes: routes.data,
        trips: trips.data,
      };
    },
  });
  const params = new URLSearchParams({
    station_id: station?.id || "",
    service_date: day,
    q,
    sort,
    limit: "50",
    offset: String(offset),
  });
  if (
    ["arrivals", "departures", "delayed", "cancelled", "platforms"].includes(
      tab,
    )
  )
    params.set("tab", tab);
  if (operator) params.set("operator_id", operator);
  if (category) params.set("category_id", category);
  if (after) params.set("after", new Date(after).toISOString());
  if (before) params.set("before", new Date(before).toISOString());
  const board = useQuery({
    queryKey: ["operations", "board", params.toString()],
    queryFn: () => api(`/operations/board?${params}`),
    enabled: !!station,
    refetchInterval: 15000,
    staleTime: 0,
  });
  const platforms = useQuery({
    queryKey: ["operations", "platforms", station?.id, operator, token],
    queryFn: () =>
      api(
        `/operations/platforms?station_id=${station!.id}&operator_id=${operator}`,
        { headers },
      ),
    enabled: !!station && !!operator && !!token,
  });
  const history = useQuery({
    queryKey: ["operations", "history", station?.id, operator, token],
    queryFn: () =>
      api(
        `/operations/events?station_id=${station!.id}&operator_id=${operator}&limit=100`,
        { headers },
      ),
    enabled: !!station && !!operator && !!token,
  });
  const disruptions = useQuery({
    queryKey: ["operations", "disruptions", station?.id, operator],
    queryFn: () =>
      api(
        `/operations/disruptions?station_id=${station!.id}&operator_id=${operator}`,
      ),
    enabled: !!station && !!operator,
  });
  const detail = useQuery({
    queryKey: ["operations", "detail", selected?.trip_id, station?.id, token],
    queryFn: () =>
      api(`/operations/trips/${selected!.trip_id}?station_id=${station!.id}`, {
        headers,
      }),
    enabled: !!selected?.trip_id && !!station && !!token,
  });
  const mutation = useMutation({
    mutationFn: async () => {
      if (!selected || !station || !source || reason.trim().length < 5)
        throw new Error(
          "Select a trip, local source and a reason of at least five characters.",
        );
      let tripId = selected.trip_id;
      if (!tripId) {
        const created = await post(
          "/operations/trips",
          {
            service_id: selected.service_id,
            service_date: selected.service_date,
            station_id: station.id,
            source_id: source,
          },
          token,
        );
        tripId = created.data.id;
      }
      const details: Row = {};
      if (["ETA", "DELAYED"].includes(kind)) {
        if (eta) details[estimateField] = new Date(eta).toISOString();
        else if (estimateField === "estimated_arrival")
          throw new Error("Enter an explicit revised arrival time.");
        else details.delay_minutes = Number(delay);
      }
      if (kind === "PLATFORM" || (kind === "BOARDING" && bay))
        details.bay_id = bay;
      if (
        ["PUBLISH_NOTICE", "PUBLISH_ANNOUNCEMENT", "CORRECTION"].includes(kind)
      )
        details.target_event_id = target;
      if (kind === "CORRECTION") details.corrected_event_type = corrected;
      if (kind === "NOTICE_REQUEST")
        Object.assign(details, {
          description,
          disruption_type: disruptionType,
          severity,
          affected_station_ids: affected
            ? affected.split(",").map((s) => s.trim())
            : [station.id],
          affected_service_ids: affectedServices,
          affected_route_ids: affectedRoutes,
          affected_trip_ids: affectedTrips,
          ...(startsAt ? { starts_at: new Date(startsAt).toISOString() } : {}),
          ...(endsAt ? { ends_at: new Date(endsAt).toISOString() } : {}),
        });
      const result = await post(
        `/operations/trips/${tripId}/events`,
        {
          event_type: kind,
          station_id: station.id,
          source_id: source,
          expected_version: selected.version,
          idempotency_key: crypto.randomUUID(),
          occurred_at: occurred
            ? new Date(occurred).toISOString()
            : new Date().toISOString(),
          expires_at: new Date(
            Date.now() + Number(expiryMinutes) * 60000,
          ).toISOString(),
          reason,
          details,
        },
        token,
      );
      return result;
    },
    onSuccess: (result) => {
      setNotice(
        `Recorded ${result.data.operation} · version ${result.data.version} · ${result.data.dataset_source}`,
      );
      setSelected(undefined);
      setReason("");
      setBay("");
      setOccurred("");
      setEta("");
      void client.invalidateQueries({ queryKey: ["operations"] });
    },
    onError: () => {
      void client.invalidateQueries({ queryKey: ["operations"] });
    },
  });
  function timeLabel(value: string | undefined) {
    return value
      ? new Date(value).toLocaleString("en-IN", {
          timeZone: station?.timezone || "Asia/Kolkata",
        })
      : "Unknown";
  }
  const d = board.data;
  return (
    <section className="operations-center">
      <div className="card-top">
        <h2>
          {passenger ? "Arrival & departure board" : "Station operations"}
        </h2>
        <Badge>{connection}</Badge>
      </div>
      <p>
        Service date is the route's origin date. Overnight stop times display
        their full date. Estimates are dispatcher input; actual movement
        requires a recorded observation.
      </p>
      <div className="panel edit-grid">
        <StationPicker
          label="Operations bus stand"
          value={station}
          onChange={(value) => {
            setStation(value);
            setSelected(undefined);
            setOffset(0);
          }}
        />
        <label className="field">
          Board operator
          <select
            aria-label="Board operator"
            value={operator}
            onChange={(e) => {
              setOperator(e.target.value);
              setSelected(undefined);
              setOffset(0);
            }}
          >
            <option value="">All operators</option>
            {options.data?.data.operators.map((o: Row) => (
              <option key={o.id} value={o.id}>
                {o.name}
              </option>
            ))}
          </select>
        </label>
        <label className="field">
          Service date
          <input
            type="date"
            value={day}
            onChange={(e) => {
              setDay(e.target.value);
              setOffset(0);
              setSelected(undefined);
            }}
          />
        </label>
        <label className="field">
          Search board
          <input
            value={q}
            onChange={(e) => {
              setQ(e.target.value);
              setOffset(0);
            }}
          />
        </label>
        <label className="field">
          Board category
          <select
            aria-label="Board category"
            value={category}
            onChange={(e) => {
              setCategory(e.target.value);
              setOffset(0);
            }}
          >
            <option value="">All categories</option>
            {options.data?.data.categories?.map((c: Row) => (
              <option key={c.id} value={c.id}>
                {c.name}
              </option>
            ))}
          </select>
        </label>
        <label className="field">
          Sort board
          <select
            aria-label="Sort board"
            value={sort}
            onChange={(e) => setSort(e.target.value)}
          >
            {[
              "scheduled_departure",
              "scheduled_arrival",
              "service_number",
              "status",
              "category",
            ].map((s) => (
              <option key={s}>{s}</option>
            ))}
          </select>
        </label>
        <label className="field">
          Window start
          <input
            type="datetime-local"
            value={after}
            onChange={(e) => {
              setAfter(e.target.value);
              setOffset(0);
            }}
          />
        </label>
        <label className="field">
          Window end
          <input
            type="datetime-local"
            value={before}
            onChange={(e) => {
              setBefore(e.target.value);
              setOffset(0);
            }}
          />
        </label>
        <Button
          variant="secondary"
          onClick={() => {
            void client.invalidateQueries({ queryKey: ["operations"] });
          }}
        >
          Refresh authoritative board
        </Button>
      </div>
      <div className="card-actions" aria-label="Actual operational counts">
        {Object.entries(d?.counts || {}).map(([name, value]) => (
          <Badge key={name}>
            {name.replaceAll("_", " ")}: {String(value)}
          </Badge>
        ))}
      </div>
      <div className="tabs" role="tablist" aria-label="Operations views">
        {[
          "arrivals",
          "departures",
          "delayed",
          "cancelled",
          "platforms",
          ...(!passenger ? ["disruptions", "history"] : []),
        ].map((value) => (
          <button
            role="tab"
            aria-selected={tab === value}
            key={value}
            onClick={() => {
              setTab(value);
              setOffset(0);
            }}
          >
            {value.charAt(0).toUpperCase() + value.slice(1)}
          </button>
        ))}
      </div>
      {board.error && <Notice error>{errorText(board.error)}</Notice>}
      {notice && <Notice>{notice}</Notice>}
      {tab === "disruptions" ? (
        <section className="panel">
          <h3>Approved local disruptions</h3>
          {disruptions.data?.data.map((r: Row) => (
            <p key={r.id}>
              <Badge>{r.severity || "Recorded"}</Badge> {r.description} ·{" "}
              {r.dataset_source} · until {timeLabel(r.expires_at)}
            </p>
          ))}
          {!operator && (
            <Notice>Select an operator to inspect scoped disruptions.</Notice>
          )}
        </section>
      ) : tab === "history" ? (
        <section className="panel">
          <h3>Append-only event history</h3>
          {history.error && <Notice error>{errorText(history.error)}</Notice>}
          <div className="table-scroll">
            <table>
              <thead>
                <tr>
                  <th>Recorded / occurred</th>
                  <th>Event / version</th>
                  <th>Actor / source</th>
                  <th>Reason / details</th>
                </tr>
              </thead>
              <tbody>
                {history.data?.data.map((r: Row) => (
                  <tr key={r.id}>
                    <td>
                      {timeLabel(r.recorded_at)}
                      <br />
                      {timeLabel(r.occurred_at)}
                    </td>
                    <td>
                      {r.operation} · {r.version}
                      <br />
                      <small>{r.id}</small>
                    </td>
                    <td>
                      {r.actor}
                      <br />
                      {r.dataset_source}
                    </td>
                    <td>
                      {r.reason}
                      <details>
                        <summary>Previous / new values</summary>
                        <pre>
                          {JSON.stringify(
                            { before: r.previous_values, after: r.new_values },
                            null,
                            2,
                          )}
                        </pre>
                      </details>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      ) : (
        <div className="table-scroll">
          <table>
            <thead>
              <tr>
                <th>Service / origin → destination</th>
                <th>Category</th>
                <th>Scheduled</th>
                <th>Estimated</th>
                <th>Actual</th>
                <th>Platform</th>
                <th>Status</th>
                <th>Last update</th>
                {!passenger && <th>Action</th>}
              </tr>
            </thead>
            <tbody>
              {d?.data.map((r: Row) => (
                <tr key={`${r.service_id}-${r.service_date}`}>
                  <td>
                    {r.service_number}
                    <br />
                    {r.origin} → {r.destination}
                    <br />
                    <Badge>{r.dataset_source}</Badge>
                  </td>
                  <td>{r.category}</td>
                  <td>
                    {timeLabel(
                      tab === "arrivals"
                        ? r.scheduled_arrival
                        : r.scheduled_departure,
                    )}
                  </td>
                  <td>
                    {timeLabel(
                      tab === "arrivals"
                        ? r.estimated_arrival
                        : r.estimated_departure,
                    )}
                    <br />
                    {r.delay_status}
                  </td>
                  <td>
                    {timeLabel(
                      tab === "arrivals"
                        ? r.actual_arrival
                        : r.actual_departure,
                    )}
                  </td>
                  <td>
                    {r.platform.bay || "Unknown"}
                    <br />
                    {r.platform.kind}
                  </td>
                  <td>
                    <Badge>{r.status}</Badge>
                    <br />
                    {r.delay_minutes === null
                      ? "Delay unknown"
                      : `${r.delay_minutes} minutes delayed`}
                  </td>
                  <td>{timeLabel(r.last_update)}</td>
                  {!passenger && (
                    <td>
                      <Button
                        variant="secondary"
                        disabled={
                          !writable || board.isFetching || mutation.isPending
                        }
                        onClick={() => {
                          setSelected(r);
                          setNotice("");
                        }}
                      >
                        Dispatch {r.service_number}
                      </Button>
                    </td>
                  )}
                </tr>
              ))}
            </tbody>
          </table>
          {!d?.data.length && (
            <Notice>
              No scheduled services match the selected station/date and filters.
            </Notice>
          )}
        </div>
      )}
      <div className="pagination">
        <Button
          disabled={!offset}
          variant="ghost"
          onClick={() => setOffset((n) => Math.max(0, n - 50))}
        >
          Previous services
        </Button>
        <span>{d?.total || 0} matching services</span>
        <Button
          disabled={offset + 50 >= (d?.total || 0)}
          variant="ghost"
          onClick={() => setOffset((n) => n + 50)}
        >
          Next services
        </Button>
      </div>
      {tab === "platforms" && !passenger && (
        <section className="panel">
          <h3>Platform assignments & conflicts</h3>
          {platforms.error && (
            <Notice error>{errorText(platforms.error)}</Notice>
          )}
          {platforms.data?.data.map((p: Row) => (
            <div key={p.bay.id} className="panel">
              Platform {p.bay.code} · physical occupancy {p.occupancy} ·{" "}
              {p.assignments.length} current/upcoming assignments ·{" "}
              {p.conflict
                ? "CONFLICT — review assignments"
                : "No recorded overlap"}
              <details>
                <summary>Current and upcoming assignments</summary>
                <div className="table-scroll">
                  <table>
                    <thead>
                      <tr>
                        <th>Service / dated trip</th>
                        <th>From</th>
                        <th>Until</th>
                        <th>Assignment kind</th>
                        <th>Provenance</th>
                      </tr>
                    </thead>
                    <tbody>
                      {p.assignments.map((a: Row) => (
                        <tr key={a.id}>
                          <td>
                            {board.data?.data.find(
                              (r: Row) => r.trip_id === a.trip_id,
                            )?.service_number || a.trip_id}
                          </td>
                          <td>{timeLabel(a.effective_at)}</td>
                          <td>{timeLabel(a.expires_at)}</td>
                          <td>
                            {a.verified
                              ? a.assignment_kind || "DISPATCHER_CONFIRMED"
                              : "PLANNED"}
                          </td>
                          <td>{a.dataset_source}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </details>
              <Button variant="ghost" onClick={() => setTab("history")}>
                View platform change history
              </Button>
            </div>
          ))}
        </section>
      )}
      {selected && (
        <section className="panel" aria-label="Dispatcher quick actions">
          <div className="card-top">
            <h3>
              Dispatch {selected.service_number} · version {selected.version}
            </h3>
            <Button variant="ghost" onClick={() => setSelected(undefined)}>
              Close dispatcher
            </Button>
          </div>
          <Notice>
            Authorized updates become visible immediately. Confirm actual
            arrival/departure only after observation. DEMO remains DEMO. On
            conflict, refresh and select the service again.
          </Notice>
          <form
            onSubmit={(e) => {
              e.preventDefault();
              setConfirm(true);
            }}
          >
            <div className="edit-grid">
              <label className="field">
                Operational action
                <select
                  aria-label="Operational action"
                  value={kind}
                  onChange={(e) => {
                    setKind(e.target.value);
                    setBay("");
                  }}
                >
                  {actions.map((a) => (
                    <option key={a}>{a}</option>
                  ))}
                </select>
              </label>
              <label className="field">
                Operational source
                <select
                  aria-label="Operational source"
                  required
                  value={source}
                  onChange={(e) => setSource(e.target.value)}
                >
                  <option value="">Select local provenance</option>
                  {sources.data?.data.map((s: Row) => (
                    <option key={s.id} value={s.id}>
                      {s.name} {s.is_demo ? "· DEMO" : "· local source"}
                    </option>
                  ))}
                </select>
              </label>
              <label className="field">
                Reason
                <input
                  required
                  minLength={5}
                  value={reason}
                  onChange={(e) => setReason(e.target.value)}
                />
              </label>
              <label className="field">
                Observed at (blank means now)
                <input
                  type="datetime-local"
                  value={occurred}
                  onChange={(e) => setOccurred(e.target.value)}
                />
              </label>
              <label className="field">
                Validity in minutes
                <input
                  type="number"
                  min="1"
                  max="10080"
                  value={expiryMinutes}
                  onChange={(e) => setExpiryMinutes(e.target.value)}
                />
              </label>
              {["ETA", "DELAYED"].includes(kind) && (
                <>
                  <label className="field">
                    Estimate type
                    <select
                      aria-label="Estimate type"
                      value={estimateField}
                      onChange={(e) => setEstimateField(e.target.value)}
                    >
                      <option value="estimated_departure">
                        Revised departure
                      </option>
                      <option value="estimated_arrival">Revised arrival</option>
                    </select>
                  </label>
                  <label className="field">
                    Delay minutes
                    <input
                      type="number"
                      min="0"
                      max="2880"
                      value={delay}
                      onChange={(e) => setDelay(e.target.value)}
                    />
                  </label>
                  <label className="field">
                    {estimateField === "estimated_arrival"
                      ? "Revised arrival"
                      : "Revised departure (overrides delay minutes)"}
                    <input
                      type="datetime-local"
                      value={eta}
                      onChange={(e) => setEta(e.target.value)}
                    />
                  </label>
                </>
              )}
              {["PLATFORM", "BOARDING"].includes(kind) && (
                <label className="field">
                  Confirmed platform
                  <select
                    aria-label="Confirmed platform"
                    required={kind === "PLATFORM"}
                    value={bay}
                    onChange={(e) => setBay(e.target.value)}
                  >
                    <option value="">Choose station platform</option>
                    {platforms.data?.data.map((p: Row) => (
                      <option key={p.bay.id} value={p.bay.id}>
                        {p.bay.code}
                      </option>
                    ))}
                  </select>
                </label>
              )}
              {[
                "PUBLISH_NOTICE",
                "PUBLISH_ANNOUNCEMENT",
                "CORRECTION",
              ].includes(kind) && (
                <label className="field">
                  Request key or correction event ID
                  {kind !== "CORRECTION" ? (
                    <select
                      aria-label="Pending request for approval"
                      required
                      value={target}
                      onChange={(e) => setTarget(e.target.value)}
                    >
                      <option value="">
                        Choose independently submitted request
                      </option>
                      {Object.entries(
                        detail.data?.data.operational_state?.pending || {},
                      )
                        .filter(
                          ([, item]) =>
                            (item as Row).kind ===
                            (kind === "PUBLISH_NOTICE"
                              ? "NOTICE_REQUEST"
                              : "ANNOUNCEMENT_REQUEST"),
                        )
                        .map(([key, item]) => (
                          <option key={key} value={key}>
                            {(item as Row).kind} · {(item as Row).actor} ·{" "}
                            {(item as Row).details.description ||
                              (item as Row).preview ||
                              "Review request"}
                          </option>
                        ))}
                    </select>
                  ) : (
                    <input
                      required
                      value={target}
                      onChange={(e) => setTarget(e.target.value)}
                    />
                  )}
                </label>
              )}
              {kind === "CORRECTION" && (
                <label className="field">
                  Corrected event type
                  <select
                    aria-label="Corrected event type"
                    value={corrected}
                    onChange={(e) => setCorrected(e.target.value)}
                  >
                    {[
                      "ARRIVED_AT_STOP",
                      "DEPARTED_FROM_STOP",
                      "BOARDING",
                      "READY",
                    ].map((k) => (
                      <option key={k}>{k}</option>
                    ))}
                  </select>
                </label>
              )}
              {kind === "NOTICE_REQUEST" && (
                <>
                  <label className="field">
                    Disruption start (blank means publication time)
                    <input
                      type="datetime-local"
                      value={startsAt}
                      onChange={(e) => setStartsAt(e.target.value)}
                    />
                  </label>
                  <label className="field">
                    Disruption end (blank uses validity above)
                    <input
                      type="datetime-local"
                      value={endsAt}
                      onChange={(e) => setEndsAt(e.target.value)}
                    />
                  </label>
                  <label className="field">
                    Affected services
                    <select
                      aria-label="Affected services"
                      multiple
                      value={affectedServices}
                      onChange={(e) =>
                        setAffectedServices(
                          Array.from(e.target.selectedOptions, (o) => o.value),
                        )
                      }
                    >
                      {references.data?.services.map((s: Row) => (
                        <option key={s.id} value={s.id}>
                          {s.number}
                        </option>
                      ))}
                    </select>
                  </label>
                  <label className="field">
                    Affected routes
                    <select
                      aria-label="Affected routes"
                      multiple
                      value={affectedRoutes}
                      onChange={(e) =>
                        setAffectedRoutes(
                          Array.from(e.target.selectedOptions, (o) => o.value),
                        )
                      }
                    >
                      {references.data?.routes.map((r: Row) => (
                        <option key={r.id} value={r.id}>
                          {r.code}
                        </option>
                      ))}
                    </select>
                  </label>
                  <label className="field">
                    Affected dated trips
                    <select
                      aria-label="Affected dated trips"
                      multiple
                      value={affectedTrips}
                      onChange={(e) =>
                        setAffectedTrips(
                          Array.from(e.target.selectedOptions, (o) => o.value),
                        )
                      }
                    >
                      {references.data?.trips.map((t: Row) => (
                        <option key={t.id} value={t.id}>
                          {references.data?.services.find(
                            (s: Row) => s.id === t.service_id,
                          )?.number || t.service_id}{" "}
                          · {t.service_date}
                        </option>
                      ))}
                    </select>
                  </label>
                  <label className="field">
                    Disruption type
                    <select
                      aria-label="Disruption type"
                      value={disruptionType}
                      onChange={(e) => setDisruptionType(e.target.value)}
                    >
                      {[
                        "ROAD_CLOSURE",
                        "ROUTE_DIVERSION",
                        "STATION_CLOSURE",
                        "STOP_SUSPENSION",
                        "FESTIVAL_CROWD",
                        "WEATHER_SUSPENSION",
                        "SERVICE_INTERRUPTION",
                        "OTHER",
                      ].map((t) => (
                        <option key={t}>{t}</option>
                      ))}
                    </select>
                  </label>
                  <label className="field">
                    Severity
                    <select
                      aria-label="Severity"
                      value={severity}
                      onChange={(e) => setSeverity(e.target.value)}
                    >
                      {["LOW", "MEDIUM", "HIGH", "CRITICAL"].map((s) => (
                        <option key={s}>{s}</option>
                      ))}
                    </select>
                  </label>
                  <label className="field">
                    Notice description
                    <textarea
                      required
                      value={description}
                      onChange={(e) => setDescription(e.target.value)}
                    />
                  </label>
                  <label className="field">
                    Affected station IDs (comma separated; blank means this
                    stand)
                    <input
                      value={affected}
                      onChange={(e) => setAffected(e.target.value)}
                    />
                  </label>
                </>
              )}
            </div>
            <Button disabled={mutation.isPending}>
              Review operational update
            </Button>
          </form>
          {mutation.error && <Notice error>{errorText(mutation.error)}</Notice>}
          {detail.data && (
            <details>
              <summary>
                Current trip, pending reviews & announcement preview
              </summary>
              <p>{detail.data.data.announcement_preview}</p>
              <pre>
                {JSON.stringify(detail.data.data.operational_state, null, 2)}
              </pre>
            </details>
          )}
          <ConfirmDialog
            open={confirm}
            onOpenChange={setConfirm}
            title={`Confirm ${kind.replaceAll("_", " ").toLowerCase()}?`}
            description={`Record this update for ${selected.service_number} at ${station?.name}. Passenger enquiries will use authorized published facts. Reason: ${reason}`}
            onConfirm={() => mutation.mutate()}
            pending={mutation.isPending}
          />
        </section>
      )}
    </section>
  );
}
