import { useEffect, useState } from "react";
import { useQueries } from "@tanstack/react-query";
import { api, dateText, fareText, timeText, type Row } from "../api";
import { Badge, Button, Notice } from "./ui";
function moneyMinor(value: unknown): bigint | null {
  if (value === null || value === undefined) return null;
  const match = String(value).match(/^(\d+)(?:\.(\d{1,2}))?$/);
  return match
    ? BigInt(match[1]) * 100n + BigInt((match[2] || "").padEnd(2, "0"))
    : null;
}
export function JourneyComparison({
  journeys,
  onClose,
}: {
  journeys: Row[];
  onClose: () => void;
}) {
  const legs: Row[] = journeys.flatMap((j) => j.legs);
  const keys = Array.from(
    new Map(
      legs.map((leg) => [`${leg.service_id}:${leg.service_date}`, leg]),
    ).values(),
  );
  const details = useQueries({
    queries: keys.map((leg) => ({
      queryKey: ["service", leg.service_id, leg.service_date],
      queryFn: ({ signal }) =>
        api(
          `/app/services/${encodeURIComponent(leg.service_id)}?travel_date=${leg.service_date}`,
          { signal },
        ),
      staleTime: 0,
      gcTime: 60000,
      refetchOnMount: "always",
    })),
  });
  const [clock, setClock] = useState(Date.now());
  const expiries = details
    .map((q) => q.data?.data.operational_expires_at)
    .filter(Boolean)
    .join("|");
  useEffect(() => {
    const now = Date.now();
    const next = expiries
      .split("|")
      .map(Date.parse)
      .filter((t) => t > now)
      .sort((a, b) => a - b)[0];
    if (!next) return;
    const timer = setTimeout(() => setClock(Date.now()), next - now + 5);
    return () => clearTimeout(timer);
  }, [expiries, clock]);
  const metadata = new Map(
    keys.map((leg, i) => [
      `${leg.service_id}:${leg.service_date}`,
      details[i].isError ? undefined : details[i].data?.data,
    ]),
  );
  const compatible = journeys.every(
    (j) =>
      j.origin === journeys[0].origin &&
      j.destination === journeys[0].destination &&
      j.currency === journeys[0].currency &&
      j.departure_at.slice(0, 10) === journeys[0].departure_at.slice(0, 10),
  );
  const arrivalsKnown =
    compatible &&
    journeys.every((j) => Number.isFinite(Date.parse(j.arrival_at)));
  const firstArrival = arrivalsKnown
    ? Math.min(...journeys.map((j) => Date.parse(j.arrival_at)))
    : null;
  const fares = journeys.map((j) => moneyMinor(j.total_fare));
  const allFares = compatible && fares.every((f) => f !== null);
  const minFare = allFares
    ? fares.reduce<bigint>((a, b) => (b !== null && b < a ? b : a), fares[0]!)
    : null;
  const knownDurations =
    compatible &&
    journeys.every(
      (j) =>
        typeof j.total_duration_minutes === "number" &&
        Number.isFinite(j.total_duration_minutes) &&
        j.total_duration_minutes >= 0 &&
        Number.isFinite(Date.parse(j.arrival_at)),
    );
  const shortest = knownDurations
    ? Math.min(...journeys.map((j) => j.total_duration_minutes))
    : null;
  const rows = [
    ["Fare", (j: Row) => fareText(j.total_fare)],
    ["Duration", (j: Row) => `${j.total_duration_minutes} min`],
    [
      "Departure",
      (j: Row) => `${dateText(j.departure_at)} ${timeText(j.departure_at)}`,
    ],
    [
      "Arrival",
      (j: Row) => `${dateText(j.arrival_at)} ${timeText(j.arrival_at)}`,
    ],
    ["Transfers", (j: Row) => String(j.transfer_count)],
    ["Bus types", (j: Row) => j.legs.map((l: Row) => l.category).join(" → ")],
    [
      "Amenities",
      (j: Row) =>
        j.legs
          .map((l: Row) => {
            const d = metadata.get(`${l.service_id}:${l.service_date}`);
            const verified = d?.amenities?.filter(
              (a: Row) => a.verified === true && a.available,
            );
            return verified?.length
              ? verified.map((a: Row) => a.name).join(", ")
              : "Not confirmed";
          })
          .join(" / "),
    ],
    ["Seats", () => "Not confirmed"],
    [
      "Platforms",
      (j: Row) =>
        j.legs
          .map((l: Row) => {
            const d = metadata.get(`${l.service_id}:${l.service_date}`);
            const expired =
              d?.operational_expires_at &&
              Date.parse(d.operational_expires_at) <=
                Math.max(clock, Date.now());
            return !expired && d?.platform?.status === "known"
              ? d.platform.bay
              : "Not confirmed";
          })
          .join(" / "),
    ],
  ] as const;
  return (
    <section className="panel comparison-panel" aria-label="Journey comparison">
      <div className="card-top">
        <div>
          <span className="eyebrow">VALIDATED AGAINST LOCAL RECORDS</span>
          <h2>Compare {journeys.length} journeys</h2>
        </div>
        <Button variant="ghost" onClick={onClose}>
          Close comparison
        </Button>
      </div>
      <div className="comparison-scroll">
        <table>
          <thead>
            <tr>
              <th>Journey information</th>
              {journeys.map((j, i) => (
                <th key={j.journey_id}>
                  Option {i + 1}
                  <div className="winner-badges">
                    {minFare !== null && fares[i] === minFare && (
                      <Badge tone="green">Lowest known fare</Badge>
                    )}
                    {shortest !== null &&
                      j.total_duration_minutes === shortest && (
                        <Badge tone="blue">Shortest known duration</Badge>
                      )}
                    {firstArrival !== null &&
                      Date.parse(j.arrival_at) === firstArrival && (
                        <Badge tone="blue">Earliest known arrival</Badge>
                      )}
                    <Badge
                      tone={j.sources.includes("DEMO") ? "amber" : "muted"}
                    >
                      {j.sources.join(", ")}
                    </Badge>
                  </div>
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {rows.map(([label, value]) => (
              <tr
                key={label}
                className={
                  new Set(journeys.map((j) => value(j))).size > 1
                    ? "different-values"
                    : ""
                }
              >
                <th>
                  {label}
                  {new Set(journeys.map((j) => value(j))).size > 1 && (
                    <small>Differs</small>
                  )}
                </th>
                {journeys.map((j) => (
                  <td key={j.journey_id}>{value(j)}</td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {(!allFares || !knownDurations) && (
        <Notice>
          Some values are missing or these options leave on different dates. No
          winner is claimed for incomplete or incompatible comparison
          dimensions.
        </Notice>
      )}
      <p className="subtle">
        Comparison uses the same submitted search constraints. Prices are per
        passenger. Unknown fares are never zero; amenities, seats and platforms
        require verified records.
      </p>
    </section>
  );
}
