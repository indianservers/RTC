import { useFreshService } from "../useFreshService";
import { Link, useParams, useSearchParams } from "react-router-dom";
import { ArrowLeft, BusFront, MapPin, Clock3 } from "lucide-react";
import { today, timeText, dateText, fareText, type Row } from "../api";
import { Badge, Notice, PageTitle, Button } from "../components/ui";
import { RouteTimeline } from "../components/RouteTimeline";
import { StatusIndicator } from "../components/StatusIndicator";
import { LoadingSkeleton, ErrorState } from "../components/feedback";
export function ServicePage() {
  const { id } = useParams();
  const [params, setParams] = useSearchParams();
  const date = params.get("date") || today();
  const tab = params.get("tab") || "overview";
  const tabs = [
    ["overview", "Overview"],
    ["stops", "Route & Stops"],
    ["fares", "Fares"],
    ["amenities", "Amenities"],
    ["operations", "Operational Status"],
  ];
  const q = useFreshService(id, date);
  const d = q.data?.data;
  if (q.isPending)
    return (
      <div className="page-container">
        <LoadingSkeleton label="Loading service details…" />
      </div>
    );
  if (q.error)
    return (
      <div className="page-container">
        <ErrorState
          message={q.error.message}
          onRetry={() => void q.refetch()}
        />
      </div>
    );
  const active = tabs.some((t) => t[0] === tab) ? tab : "overview";
  const confirmedAmenities = d.amenities.filter(
    (a: Row) => a.verified === true,
  );
  const stats = (
    <dl className="detail-grid">
      <dt>Air conditioning</dt>
      <dd>
        {d.vehicle_type?.ac == null
          ? "Not confirmed"
          : d.vehicle_type.ac
            ? "AC"
            : "Non-AC"}
      </dd>
      <dt>Configuration</dt>
      <dd>
        {d.vehicle_type?.sleeper == null
          ? "Not confirmed"
          : d.vehicle_type.sleeper
            ? "Sleeper"
            : "Seater"}
      </dd>
      <dt>Platform</dt>
      <dd>{d.platform?.bay || "Not confirmed"}</dd>
      <dt>Seat inventory</dt>
      <dd>Not confirmed</dd>
      <dt>Source</dt>
      <dd>{d.service.dataset_source}</dd>
    </dl>
  );
  return (
    <div className="page-container">
      <Link className="text-link" to="/">
        <ArrowLeft size={16} />
        Back to enquiry
      </Link>
      <PageTitle
        eyebrow="SERVICE DETAILS"
        title={`Service ${d.service.number}`}
        description={`${d.operator?.name || "Operator not available"} · ${d.category?.name || "Category not available"}`}
        actions={
          <Badge tone={d.service.dataset_source === "DEMO" ? "amber" : "muted"}>
            {d.service.dataset_source}
          </Badge>
        }
      />
      <div
        role="tablist"
        aria-label="Service information"
        className="detail-tabs"
      >
        {tabs.map(([key, label], i) => (
          <button
            role="tab"
            key={key}
            id={`tab-${key}`}
            aria-selected={active === key}
            aria-controls={`panel-${key}`}
            tabIndex={active === key ? 0 : -1}
            onKeyDown={(e) => {
              if (["ArrowLeft", "ArrowRight", "Home", "End"].includes(e.key)) {
                e.preventDefault();
                const next =
                  e.key === "Home"
                    ? 0
                    : e.key === "End"
                      ? tabs.length - 1
                      : (i + (e.key === "ArrowRight" ? 1 : -1) + tabs.length) %
                        tabs.length;
                setParams({
                  ...Object.fromEntries(params),
                  tab: tabs[next][0],
                });
                requestAnimationFrame(() =>
                  document.getElementById(`tab-${tabs[next][0]}`)?.focus(),
                );
              }
            }}
            onClick={() =>
              setParams({ ...Object.fromEntries(params), tab: key })
            }
          >
            {label}
          </button>
        ))}
      </div>
      <section
        className="panel tab-panel"
        role="tabpanel"
        id={`panel-${active}`}
        aria-labelledby={`tab-${active}`}
        tabIndex={0}
      >
        {active === "overview" && (
          <>
            <h2>
              <BusFront size={20} />
              Journey overview
            </h2>
            <div className="overview-route">
              <div>
                <strong>
                  {d.stops[0]?.station_name || "Origin not available"}
                </strong>
                <span>
                  {timeText(d.journey?.departure)} ·{" "}
                  {d.journey?.departure ? dateText(d.journey.departure) : date}
                </span>
              </div>
              <span>→</span>
              <div>
                <strong>
                  {d.stops.at(-1)?.station_name || "Destination not available"}
                </strong>
                <span>
                  {timeText(d.journey?.arrival)} ·{" "}
                  {d.journey?.arrival ? dateText(d.journey.arrival) : date}
                </span>
              </div>
            </div>
            <StatusIndicator
              status={d.status.status}
              verifiedAt={d.status.last_verified_at}
            />
            {stats}
            <Button
              variant="secondary"
              onClick={() =>
                setParams({ ...Object.fromEntries(params), tab: "stops" })
              }
            >
              View ordered stops
            </Button>
          </>
        )}
        {active === "stops" && (
          <>
            <h2>
              <MapPin size={20} />
              Route & stops
            </h2>
            <p className="subtle">
              {date} · Scheduled times from local route offsets; not live
              tracking.
            </p>
            <RouteTimeline stops={d.stops} />
          </>
        )}
        {active === "fares" && (
          <>
            <h2>Fare information</h2>
            <dl className="detail-grid">
              <dt>Full listed route fare</dt>
              <dd>{fareText(d.fare?.total)}</dd>
              <dt>Fare status</dt>
              <dd>{d.fare?.fare_status || "UNKNOWN"}</dd>
              <dt>Source</dt>
              <dd>{d.fare?.source || "Not available"}</dd>
              <dt>Concession eligibility</dt>
              <dd>{d.fare?.concession_eligibility || "Not evaluated"}</dd>
              <dt>Surcharge</dt>
              <dd>{fareText(d.fare?.surcharge)}</dd>
            </dl>
            <h3>Recorded concessions</h3>
            {d.concessions?.length ? (
              d.concessions.map((c: Row) => (
                <div className="concession-record" key={c.name}>
                  <strong>
                    {c.name} · {c.percent}%
                  </strong>
                  <p>Criteria: {c.criteria.join(", ") || "Not recorded"}</p>
                  <small>
                    {c.dataset_source} · Eligibility{" "}
                    {c.eligibility_confirmed ? "confirmed" : "not confirmed"}
                  </small>
                </div>
              ))
            ) : (
              <p className="subtle">
                No valid concession records are available for this operator and
                date.
              </p>
            )}
            <Notice>
              Fares apply to the full listed route where known. Ask the enquiry
              engine for your boarding segment. Unknown concessions and charges
              are not assumed to be zero.
            </Notice>
          </>
        )}
        {active === "amenities" && (
          <>
            <h2>Verified amenities</h2>
            {confirmedAmenities.length ? (
              confirmedAmenities.map((a: Row) => (
                <p key={a.id}>
                  {a.name}:{" "}
                  {a.available
                    ? "Verified as available"
                    : "Verified as unavailable"}
                </p>
              ))
            ) : (
              <Notice>
                No verified amenity properties are supplied by the current local
                records.
              </Notice>
            )}
            <details>
              <summary>
                Reference properties (not operationally verified)
              </summary>
              {stats}
              <p className="subtle">
                Catalogued amenities:{" "}
                {d.amenities.map((a: Row) => a.name).join(", ") ||
                  "Not available"}
                . These are not confirmations of availability.
              </p>
            </details>
          </>
        )}
        {active === "operations" && (
          <>
            <h2>
              <Clock3 size={20} />
              Operational status
            </h2>
            <StatusIndicator
              status={d.status.status}
              verifiedAt={d.status.last_verified_at}
            />
            <dl className="detail-grid">
              <dt>GPS freshness</dt>
              <dd>{d.status.gps_status || "UNKNOWN"}</dd>
              <dt>Verified delay</dt>
              <dd>
                {d.status.delay_status === "KNOWN"
                  ? `${d.status.delay_minutes} minutes`
                  : "Not confirmed"}
              </dd>
              <dt>Platform</dt>
              <dd>{d.platform?.bay || "Not confirmed"}</dd>
              <dt>Platform effective time</dt>
              <dd>
                {d.platform?.effective_at
                  ? new Date(d.platform.effective_at).toLocaleString("en-IN")
                  : "Not available"}
              </dd>
              <dt>Latest verified location time</dt>
              <dd>
                {d.status.last_verified_at
                  ? new Date(d.status.last_verified_at).toLocaleString("en-IN")
                  : "Not available"}
              </dd>
            </dl>
            <Button
              variant="secondary"
              disabled={q.isFetching}
              onClick={() => void q.refetch()}
            >
              Refresh local status
            </Button>
            <Notice>
              Refresh reads local records only. Scheduled, estimated, stale and
              unknown information do not imply live GPS or confirmed seats.
            </Notice>
          </>
        )}
      </section>
    </div>
  );
}
