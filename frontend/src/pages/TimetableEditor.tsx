import { useState } from "react";
import { useQuery, useMutation } from "@tanstack/react-query";
import { api, post, errorText, type Row } from "../api";
import { Button, Notice } from "../components/ui";
export function TimetableEditor({ token }: { token: string }) {
  const headers = { Authorization: `Bearer ${token}` };
  const services = useQuery({
    queryKey: ["timetable-editor-options", token],
    queryFn: () => api("/admin/schedules?limit=100", { headers }),
  });
  const [copyNumber, setCopyNumber] = useState("");
  const [calendarStart, setCalendarStart] = useState(
    new Date().toISOString().slice(0, 10),
  );
  const [calendar, setCalendar] = useState<Row[]>([]);
  const [service, setService] = useState<Row>();
  const [rows, setRows] = useState<Row[]>([]);
  const [shift, setShift] = useState(0);
  const [error, setError] = useState("");
  const [batch, setBatch] = useState("");
  async function load(id: string) {
    setError("");
    setBatch("");
    const s = services.data?.data.find((r: Row) => r.id === id);
    setService(s);
    if (!s) {
      setRows([]);
      return;
    }
    try {
      const [stops, times] = await Promise.all([
        api(
          `/admin/stops?q=${encodeURIComponent(s.route_id)}&active=true&limit=100`,
          { headers },
        ),
        api(
          `/admin/stop-times?q=${encodeURIComponent(id)}&active=true&limit=100`,
          { headers },
        ),
      ]);
      setRows(
        stops.data
          .filter((r: Row) => r.route_id === s.route_id)
          .sort((a: Row, b: Row) => a.sequence - b.sequence)
          .map((r: Row) => {
            const time = times.data.find(
              (t: Row) => t.stop_id === r.id && t.service_id === id,
            );
            return {
              id: time?.id || crypto.randomUUID(),
              stop_id: r.id,
              station_id: r.station_id,
              arrival_offset:
                time?.arrival_offset ??
                r.arrival_offset_minutes ??
                r.offset_minutes,
              departure_offset:
                time?.departure_offset ??
                r.departure_offset_minutes ??
                r.offset_minutes,
              existing: !!time,
              dataset_source: time?.dataset_source || s.dataset_source,
            };
          }),
      );
    } catch (e) {
      setError(errorText(e));
    }
  }
  const save = useMutation({
    mutationFn: () => {
      if (!service || !rows.length)
        throw new Error("Choose a service with a complete route.");
      return post(
        "/admin/data/changes",
        {
          operator_id: service.operator_id,
          source_id: sessionStorage.getItem("rtc-admin-source") || null,
          reason: "Stop-wise timetable editor",
          commands: rows.map((r) => ({
            resource: "stop-times",
            id: r.id,
            operation: r.existing ? "UPDATE" : "CREATE",
            values: {
              service_id: service.id,
              stop_id: r.stop_id,
              arrival_offset: r.arrival_offset,
              departure_offset: r.departure_offset,
              dataset_source: r.dataset_source,
            },
          })),
        },
        token,
      );
    },
    onSuccess: (r) => setBatch(r.data.id),
    onError: (e) => setError(errorText(e)),
  });
  return (
    <section className="panel">
      <h2>Stop-wise timetable editor</h2>
      <p>
        Times are elapsed minutes after the recurring service departure. For
        example, 1,560 is next day + 2 hours. No same-day wrapping is applied.
      </p>
      <label className="field">
        Timetable service
        <select
          aria-label="Timetable service"
          value={service?.id || ""}
          onChange={(e) => void load(e.target.value)}
        >
          <option value="">Choose a local service</option>
          {services.data?.data.map((s: Row) => (
            <option key={s.id} value={s.id}>
              {s.number}
            </option>
          ))}
        </select>
      </label>
      {service && (
        <p>
          Recurring departure:{" "}
          {Math.floor(service.departure_minutes / 60)
            .toString()
            .padStart(2, "0")}
          :{(service.departure_minutes % 60).toString().padStart(2, "0")} ·
          valid {service.valid_from} through {service.valid_to}.
        </p>
      )}
      {service && (
        <div className="edit-grid">
          <label className="field">
            Copy recurring service as number
            <input
              value={copyNumber}
              onChange={(e) => setCopyNumber(e.target.value)}
            />
          </label>
          <Button
            variant="secondary"
            disabled={!copyNumber}
            onClick={async () => {
              try {
                const r = await post(
                  `/admin/data/copy-service/${service.id}`,
                  { number: copyNumber },
                  token,
                );
                setBatch(r.data.id);
              } catch (e) {
                setError(errorText(e));
              }
            }}
          >
            Create service-copy draft
          </Button>
          <label className="field">
            Calendar preview date
            <input
              type="date"
              value={calendarStart}
              onChange={(e) => setCalendarStart(e.target.value)}
            />
          </label>
          <Button
            variant="secondary"
            onClick={async () => {
              try {
                const end = new Date(calendarStart + "T00:00:00Z");
                end.setUTCDate(end.getUTCDate() + 6);
                const r = await api(
                  `/admin/data/calendar-preview/${service.id}?start=${calendarStart}&end=${end.toISOString().slice(0, 10)}`,
                  { headers },
                );
                setCalendar(r.data);
              } catch (e) {
                setError(errorText(e));
              }
            }}
          >
            Preview seven-day calendar
          </Button>
        </div>
      )}
      {calendar.length > 0 && (
        <div aria-label="Published calendar preview">
          {calendar.map((day) => (
            <p key={day.date}>
              {day.date}: {day.operates ? "Operating" : "Not operating"} ·
              published local calendar
              {day.exception ? " / approved exception" : ""}
            </p>
          ))}
        </div>
      )}
      <div className="filter-bar">
        <label className="field">
          Bulk offset adjustment (minutes)
          <input
            type="number"
            value={shift}
            onChange={(e) => setShift(Number(e.target.value))}
          />
        </label>
        <Button
          variant="secondary"
          disabled={!rows.length}
          onClick={() =>
            setRows((old) =>
              old.map((r) => ({
                ...r,
                arrival_offset: r.arrival_offset + shift,
                departure_offset: r.departure_offset + shift,
              })),
            )
          }
        >
          Preview bulk time shift
        </Button>
      </div>
      <div className="table-scroll">
        <table>
          <thead>
            <tr>
              <th>Route stop</th>
              <th>Arrival elapsed minutes</th>
              <th>Departure elapsed minutes</th>
              <th>Day offset</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((r, index) => (
              <tr key={r.id}>
                <td>
                  {index + 1}. {r.station_id}
                </td>
                <td>
                  <input
                    aria-label={`Arrival offset stop ${index + 1}`}
                    type="number"
                    min="0"
                    value={r.arrival_offset}
                    onChange={(e) =>
                      setRows((old) =>
                        old.map((row) =>
                          row.id === r.id
                            ? { ...row, arrival_offset: Number(e.target.value) }
                            : row,
                        ),
                      )
                    }
                  />
                </td>
                <td>
                  <input
                    aria-label={`Departure offset stop ${index + 1}`}
                    type="number"
                    min="0"
                    value={r.departure_offset}
                    onChange={(e) =>
                      setRows((old) =>
                        old.map((row) =>
                          row.id === r.id
                            ? {
                                ...row,
                                departure_offset: Number(e.target.value),
                              }
                            : row,
                        ),
                      )
                    }
                  />
                </td>
                <td>
                  Day +
                  {Math.floor(
                    (service?.departure_minutes + r.arrival_offset) / 1440,
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {error && <Notice error>{error}</Notice>}
      {batch && (
        <Notice>
          Timetable saved as a draft.{" "}
          <a href={`/admin/imports?batch=${batch}`}>
            Validate, approve and publish
          </a>
        </Notice>
      )}
      <Button
        disabled={save.isPending || !service}
        onClick={() => save.mutate()}
      >
        Save timetable draft
      </Button>
    </section>
  );
}
