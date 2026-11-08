import { ArrowDown, ArrowRight, Clock3, Route } from "lucide-react";
import { Link } from "react-router-dom";
import { useQueries } from "@tanstack/react-query";
import { api, fareText, dateText, timeText, type Row } from "../api";
import { Badge, Button } from "./ui";
export function JourneyCard({
  journey,
  index,
  onSelect,
  stationNames = {},
}: {
  journey: Row;
  index?: number;
  onSelect?: (n: number) => void;
  stationNames?: Record<string, string>;
}) {
  const ids: string[] = Array.from(
    new Set<string>(
      (journey.legs || []).flatMap((leg: Row) => [leg.origin, leg.destination]),
    ),
  );
  const labels = useQueries({
    queries: ids.map((id) => ({
      queryKey: ["station-label", id],
      queryFn: () => api(`/stations/resolve?value=${encodeURIComponent(id)}`),
    })),
  });
  const names = { ...stationNames };
  labels.forEach((query, i) => {
    const candidate = query.data?.data.candidates?.[0];
    if (candidate) names[ids[i]] = candidate.name;
  });
  return (
    <article className="journey-card">
      <div className="card-top">
        <strong>
          <Route size={18} />{" "}
          {journey.transfer_count ? "Connecting journey" : "Direct journey"}
        </strong>
        <Badge tone={journey.sources?.includes("DEMO") ? "amber" : "muted"}>
          {journey.sources?.join(", ") || "Local record"}
        </Badge>
      </div>
      <div className="journey-summary">
        <strong>
          {timeText(journey.departure_at)} <ArrowRight size={18} />{" "}
          {timeText(journey.arrival_at)}
        </strong>
        <strong>{fareText(journey.total_fare)}</strong>
      </div>
      <p className="subtle">
        {dateText(journey.departure_at)} → {dateText(journey.arrival_at)} ·{" "}
        {journey.transfer_count} transfer(s) · {journey.total_duration_minutes}{" "}
        min total · {journey.total_wait_minutes} min waiting · Fare{" "}
        {String(journey.fare_status).toLowerCase()}
      </p>
      {journey.fare_status === "PARTIAL" && (
        <p className="subtle">
          Known subtotal: {fareText(journey.known_subtotal)}; total fare is not
          confirmed.
        </p>
      )}
      <div className="journey-legs">
        {journey.legs?.map((leg: Row, i: number) => (
          <div key={`${leg.service_id}-${i}`}>
            <div className="leg">
              <span className="leg-dot" />
              <div>
                <strong>
                  {names[leg.origin] || "Station not available"}{" "}
                  <ArrowRight size={12} />{" "}
                  {names[leg.destination] || "Station not available"}
                </strong>
                <p>
                  {leg.service_id} · {leg.category} ·{" "}
                  {timeText(leg.boarding_at)}–{timeText(leg.alighting_at)} ·{" "}
                  {fareText(leg.fare)}
                </p>
                <small>
                  {leg.departure_kind} ·{" "}
                  {leg.operational_status?.gps_status === "KNOWN"
                    ? "Location verified at search time; current position not confirmed"
                    : "Live location not confirmed"}
                </small>
                <Link
                  to={`/services/${leg.service_id}?date=${leg.service_date}`}
                >
                  Service details
                </Link>
              </div>
            </div>
            {journey.transfers?.[i] && (
              <div className="transfer">
                <ArrowDown size={13} />
                {journey.transfers[i].wait_minutes} min at{" "}
                {names[journey.transfers[i].station_id] ||
                  "Station not available"}
              </div>
            )}
          </div>
        ))}
      </div>
      {onSelect && index !== undefined && (
        <Button variant="secondary" onClick={() => onSelect(index)}>
          Select journey option {index}
        </Button>
      )}
      <small className="subtle">
        <Clock3 size={12} /> Scheduled connections are not guaranteed. Seat
        availability is not confirmed.
      </small>
    </article>
  );
}
