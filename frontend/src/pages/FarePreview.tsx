import { useState } from "react";
import { useQuery, useMutation } from "@tanstack/react-query";
import { api, post, today, errorText, type Row, type Station } from "../api";
import { StationPicker } from "../components/StationPicker";
import { Button, Notice } from "../components/ui";
export function FarePreview({
  token,
  batchId,
}: {
  token: string;
  batchId?: string;
}) {
  const [service, setService] = useState("");
  const [origin, setOrigin] = useState<Station>();
  const [destination, setDestination] = useState<Station>();
  const [day, setDay] = useState(today());
  const [draft, setDraft] = useState("");
  const services = useQuery({
    queryKey: ["fare-preview-services", token],
    queryFn: () =>
      api("/admin/schedules?limit=100", {
        headers: { Authorization: `Bearer ${token}` },
      }),
  });
  const quote = useMutation({
    mutationFn: () =>
      post(
        "/admin/data/fare-preview",
        {
          service_id: service,
          origin_id: origin?.id,
          destination_id: destination?.id,
          travel_date: day,
          batch_id: batchId || draft || undefined,
        },
        token,
      ),
  });
  return (
    <details className="panel">
      <summary>
        Fare calculation preview — published data or a validated draft
      </summary>
      <p>
        Preview is transactional and changes no live records.
        Eligibility-dependent concessions are not applied automatically.
      </p>
      <div className="edit-grid">
        <label className="field">
          Fare preview service
          <select value={service} onChange={(e) => setService(e.target.value)}>
            <option value="">Choose a service</option>
            {services.data?.data.map((r: Row) => (
              <option key={r.id} value={r.id}>
                {r.number}
              </option>
            ))}
          </select>
        </label>
        <StationPicker
          label="Fare boarding station"
          value={origin}
          onChange={setOrigin}
        />
        <StationPicker
          label="Fare alighting station"
          value={destination}
          onChange={setDestination}
        />
        <label className="field">
          Fare travel date
          <input
            type="date"
            value={day}
            onChange={(e) => setDay(e.target.value)}
          />
        </label>
        {!batchId && (
          <label className="field">
            Validated draft batch ID (optional)
            <input value={draft} onChange={(e) => setDraft(e.target.value)} />
          </label>
        )}
      </div>
      <Button
        disabled={!service || !origin || !destination || quote.isPending}
        onClick={() => quote.mutate()}
      >
        Calculate fare preview
      </Button>
      {quote.error && <Notice error>{errorText(quote.error)}</Notice>}
      {quote.data && (
        <div aria-label="Fare calculation result">
          <p>
            Base: {quote.data.data.base_fare ?? "Unknown"} · surcharge:{" "}
            {quote.data.data.surcharge ?? "Not recorded"} · total INR{" "}
            {quote.data.data.total ?? "Unknown"}
          </p>
          <p>
            Basis: {quote.data.data.basis || quote.data.data.fare_status}.
            Source: {quote.data.data.source || "Not confirmed"}.
          </p>
        </div>
      )}
    </details>
  );
}
