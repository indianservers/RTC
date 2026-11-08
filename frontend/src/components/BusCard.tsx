import { useFreshService } from "../useFreshService";
import { Link } from "react-router-dom";
import {
  ArrowRight,
  BusFront,
  Clock3,
  MapPin,
  Check,
  GitCompareArrows,
} from "lucide-react";
import { dateText, timeText, today, type Row } from "../api";
import { Badge, Button } from "./ui";
import { FareBadge } from "./FareBadge";
import { StatusIndicator } from "./StatusIndicator";
export function BusCard({
  row,
  index,
  onSelect,
  onAsk,
  onCompare,
  liveRefresh = true,
}: {
  row: Row;
  index?: number;
  onSelect?: (n: number) => void;
  onAsk?: (n: number) => void;
  onCompare?: () => void;
  liveRefresh?: boolean;
}) {
  const details = useFreshService(
    row.service_id,
    row.service_date || today(),
    liveRefresh,
  );
  const d = details.data?.data;
  const departure = row.departure || row.boarding_at;
  const arrival = row.arrival || row.alighting_at;
  const minutes =
    departure && arrival
      ? Math.round((Date.parse(arrival) - Date.parse(departure)) / 60000)
      : null;
  const type = d?.vehicle_type;
  const demo =
    row.dataset_source === "DEMO" ||
    row.dataset_source === "SYNTHETIC" ||
    d?.service.dataset_source === "DEMO";
  return (
    <article className="bus-card">
      <div className="card-top">
        <div className="service-brand">
          <span className="bus-icon">
            <BusFront size={20} />
          </span>
          <div>
            <strong>
              {row.service_number || d?.service.number || row.service_id}
            </strong>
            <small>
              {d?.operator?.name || "Operator not available"} ·{" "}
              {row.category_name ||
                d?.category?.name ||
                "Category not available"}
            </small>
          </div>
        </div>
        <Badge tone={demo ? "amber" : "muted"}>
          {demo ? "DEMO" : "Local record"}
        </Badge>
      </div>
      <div className="bus-times">
        <div>
          <strong>{timeText(departure)}</strong>
          <small className="service-date">{dateText(departure)}</small>
          <span>
            {d?.stops?.find(
              (s: Row) => s.station_id === (row.origin_id || row.origin),
            )?.station_name ||
              d?.stops?.[0]?.station_name ||
              row.origin ||
              "Origin not available"}
          </span>
        </div>
        <div className="trip-line">
          <small>
            {minutes === null
              ? "Duration not available"
              : `${Math.floor(minutes / 60)}h ${minutes % 60}m`}
          </small>
          <span>
            <i />
            <ArrowRight size={15} />
          </span>
        </div>
        <div>
          <strong>{timeText(arrival)}</strong>
          <small className="service-date">{dateText(arrival)}</small>
          <span>
            {d?.stops?.find(
              (s: Row) =>
                s.station_id === (row.destination_id || row.destination),
            )?.station_name ||
              d?.stops?.at(-1)?.station_name ||
              row.destination ||
              "Destination not available"}
          </span>
        </div>
        <FareBadge value={row.fare} />
      </div>
      <div className="facts">
        <span>
          <Clock3 size={13} />
          {row.departure_kind || "Scheduled"} information
        </span>
        <span>
          <MapPin size={13} />
          Platform {d?.platform?.bay || "not confirmed"}
        </span>
        <span>
          {type?.ac == null ? "AC not confirmed" : type.ac ? "AC" : "Non-AC"}
        </span>
        <span>
          {type?.sleeper == null
            ? "Configuration not confirmed"
            : type.sleeper
              ? "Sleeper"
              : "Seater"}
        </span>
        <span>Seats not confirmed</span>
        <span>
          Last verified update {d?.status?.last_verified_at || "not confirmed"}
        </span>
      </div>
      <div className="service-state">
        <StatusIndicator
          status={d?.status?.status || row.departure_kind || "SCHEDULED_ONLY"}
          verifiedAt={d?.status?.last_verified_at}
        />
        <span>Live location: {d?.status?.gps_status || "UNKNOWN"}</span>
      </div>
      <div className="card-actions">
        {onSelect && index !== undefined && (
          <Button variant="secondary" onClick={() => onSelect(index)}>
            <Check size={14} />
            Select this bus
          </Button>
        )}
        <Link
          className="text-link"
          to={`/services/${row.service_id}?date=${row.service_date || today()}&tab=stops`}
        >
          View stops <ArrowRight size={13} />
        </Link>
        <Link
          className="text-link"
          to={`/services/${row.service_id}?date=${row.service_date || today()}`}
        >
          View details
        </Link>
        {onCompare && (
          <button className="text-link" onClick={onCompare}>
            <GitCompareArrows size={14} />
            Compare
          </button>
        )}
        {onAsk && index !== undefined && (
          <button className="text-link" onClick={() => onAsk(index)}>
            Ask about this bus
          </button>
        )}
      </div>
    </article>
  );
}
