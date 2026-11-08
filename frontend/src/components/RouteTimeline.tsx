import { dateText, timeText, type Row } from "../api";
export function RouteTimeline({ stops }: { stops: Row[] }) {
  return (
    <ol className="timeline">
      {[...stops]
        .sort((a, b) => a.sequence - b.sequence)
        .map((stop) => (
          <li key={stop.id}>
            <span className="timeline-marker" />
            <div>
              <strong>
                {stop.station_name ||
                  stop.station_id ||
                  "Station not available"}
              </strong>
              <p>
                {stop.boarding ? "Boarding allowed" : "No boarding"} ·{" "}
                {stop.alighting ? "Alighting allowed" : "No alighting"}
              </p>
              <small>
                {stop.distance_km ?? "Unknown"} km from route origin · Stop{" "}
                {stop.sequence}
              </small>
            </div>
            <time>
              {timeText(stop.scheduled_at)}
              <small>
                {stop.scheduled_at
                  ? dateText(stop.scheduled_at)
                  : "Time not available"}
              </small>
            </time>
          </li>
        ))}
    </ol>
  );
}
