import { useState } from "react";
import { useQuery, useMutation } from "@tanstack/react-query";
import { api, post, errorText, type Row, type Station } from "../api";
import { StationPicker } from "../components/StationPicker";
import { Button, Notice } from "../components/ui";
export function RouteEditor({ token }: { token: string }) {
  const headers = { Authorization: `Bearer ${token}` };
  const routes = useQuery({
    queryKey: ["route-editor-options", token],
    queryFn: () => api("/admin/routes?limit=100", { headers }),
  });
  const meta = useQuery({
    queryKey: ["admin-editor-meta", token],
    queryFn: () => api("/admin/ui/metadata", { headers }),
  });
  const variants = useQuery({
    queryKey: ["route-variant-options", token],
    queryFn: () => api("/admin/route-variants?limit=100", { headers }),
  });
  const [variant, setVariant] = useState("");
  const [variantName, setVariantName] = useState("");
  const [excludedVariantStops, setExcludedVariantStops] = useState<string[]>(
    [],
  );
  const [direction, setDirection] = useState("");
  const [copySource, setCopySource] = useState("");
  const [copyOperator, setCopyOperator] = useState("");
  const [base, setBase] = useState<Row>();
  const [code, setCode] = useState("");
  const [stops, setStops] = useState<Row[]>([]);
  const [removed, setRemoved] = useState<Row[]>([]);
  const [station, setStation] = useState<Station>();
  const [error, setError] = useState("");
  const [batch, setBatch] = useState("");
  function values(resource: string, row: Row) {
    return Object.fromEntries(
      Object.keys(meta.data?.data.resources[resource].schema.properties || {})
        .filter((k) => row[k] !== undefined)
        .map((k) => [k, row[k]]),
    );
  }
  async function load(id: string) {
    setError("");
    setBatch("");
    setRemoved([]);
    setExcludedVariantStops([]);
    const route = routes.data?.data.find((r: Row) => r.id === id);
    setBase(route);
    setCode(route?.code || "");
    setDirection(route?.direction || "");
    try {
      const rows = await api(
        `/admin/stops?q=${encodeURIComponent(id)}&limit=100&active=true`,
        { headers },
      );
      setStops(
        rows.data
          .filter((s: Row) => s.route_id === id)
          .sort((a: Row, b: Row) => a.sequence - b.sequence)
          .map((s: Row) => ({ ...s, existing: true })),
      );
    } catch (e) {
      setError(errorText(e));
    }
  }
  const save = useMutation({
    mutationFn: () => {
      const operator =
        base?.operator_id ||
        copyOperator ||
        sessionStorage.getItem("rtc-admin-operator");
      if (!operator)
        throw new Error(
          "Choose the managing operator above before creating a route.",
        );
      if (stops.length < 2) throw new Error("Add at least two stops.");
      if (!code.trim()) throw new Error("Enter a unique route code.");
      const id = base?.id || crypto.randomUUID();
      const source = base?.dataset_source || copySource || "LOCAL_IMPORT";
      const commands: Row[] = [
        {
          resource: "routes",
          id,
          operation: base ? "UPDATE" : "CREATE",
          values: values("routes", {
            ...base,
            code,
            direction: direction || null,
            operator_id: operator,
            origin_station_id: stops[0].station_id,
            destination_station_id: stops.at(-1)?.station_id,
            dataset_source: source,
          }),
        },
      ];
      stops.forEach((s, index) =>
        commands.push({
          resource: "stops",
          id: s.id,
          operation: s.existing ? "UPDATE" : "CREATE",
          values: values("stops", {
            ...s,
            route_id: id,
            sequence: index,
            dataset_source: s.dataset_source || source,
          }),
        }),
      );
      removed.forEach((s) =>
        commands.push({
          resource: "stops",
          id: s.id,
          operation: "DEACTIVATE",
          values: {},
        }),
      );
      return post(
        "/admin/data/changes",
        {
          commands,
          operator_id: operator,
          source_id: sessionStorage.getItem("rtc-admin-source") || null,
          reason: "Route editor ordered-stop update",
        },
        token,
      );
    },
    onSuccess: (r) => setBatch(r.data.id),
    onError: (e) => setError(errorText(e)),
  });
  function move(index: number, delta: number) {
    setStops((old) => {
      const next = [...old];
      [next[index], next[index + delta]] = [next[index + delta], next[index]];
      return next;
    });
  }
  return (
    <section className="panel">
      <h2>Route & stop editor</h2>
      <p>
        Elapsed offsets support overnight journeys. Passing through does not
        grant boarding or alighting permission. Saving creates one atomic draft.
      </p>
      <div className="edit-grid">
        <label className="field">
          Existing route
          <select
            aria-label="Existing route"
            value={base?.id || ""}
            onChange={(e) => void load(e.target.value)}
          >
            <option value="">New route</option>
            {routes.data?.data.map((r: Row) => (
              <option key={r.id} value={r.id}>
                {r.code}
              </option>
            ))}
          </select>
        </label>
        <label className="field">
          Route direction
          <select
            value={direction}
            onChange={(e) => setDirection(e.target.value)}
          >
            <option value="">Not recorded</option>
            {["OUTBOUND", "INBOUND", "LOOP", "OTHER"].map((d) => (
              <option key={d}>{d}</option>
            ))}
          </select>
        </label>
        <label className="field">
          Route code
          <input value={code} onChange={(e) => setCode(e.target.value)} />
        </label>
      </div>
      <div className="card-actions">
        <Button
          variant="secondary"
          disabled={!base}
          onClick={() => {
            setCopySource(base?.dataset_source || "");
            setCopyOperator(base?.operator_id || "");
            setBase(undefined);
            setCode(code + "-COPY");
            setRemoved([]);
            setStops((old) =>
              old.map((s) => ({
                ...s,
                id: crypto.randomUUID(),
                existing: false,
              })),
            );
          }}
        >
          Copy as a new route
        </Button>
      </div>
      {base && (
        <div className="edit-grid">
          <label className="field">
            Existing route variant
            <select
              value={variant}
              onChange={(e) => setVariant(e.target.value)}
            >
              <option value="">Choose variant to duplicate</option>
              {variants.data?.data
                .filter((r: Row) => r.route_id === base.id)
                .map((r: Row) => (
                  <option key={r.id} value={r.id}>
                    {r.name}
                  </option>
                ))}
            </select>
          </label>
          <label className="field">
            New variant name
            <input
              value={variantName}
              onChange={(e) => setVariantName(e.target.value)}
            />
          </label>
          <Button
            variant="secondary"
            disabled={!variant || !variantName}
            onClick={async () => {
              try {
                const r = await post(
                  `/admin/data/copy-variant/${variant}`,
                  { name: variantName },
                  token,
                );
                setBatch(r.data.id);
              } catch (e) {
                setError(errorText(e));
              }
            }}
          >
            Create variant-copy draft
          </Button>
          <div>
            <p>Select published stops for a new variant, in route order.</p>
            {stops
              .filter((stop) => stop.existing)
              .map((stop, index) => (
                <label key={stop.id} className="field">
                  <span>
                    <input
                      type="checkbox"
                      checked={!excludedVariantStops.includes(stop.id)}
                      onChange={(event) =>
                        setExcludedVariantStops((ids) =>
                          event.target.checked
                            ? ids.filter((id) => id !== stop.id)
                            : [...ids, stop.id],
                        )
                      }
                    />
                    {index + 1}. {stop.station_id}
                  </span>
                </label>
              ))}
            <Button
              variant="secondary"
              disabled={
                !variantName.trim() || stops.some((stop) => !stop.existing)
              }
              onClick={async () => {
                try {
                  const members = stops.filter(
                    (stop) => !excludedVariantStops.includes(stop.id),
                  );
                  if (members.length < 2)
                    throw new Error("Select at least two published stops.");
                  const id = crypto.randomUUID();
                  const source = base.dataset_source;
                  const result = await post(
                    "/admin/data/changes",
                    {
                      operator_id: base.operator_id,
                      source_id:
                        sessionStorage.getItem("rtc-admin-source") || null,
                      reason:
                        "Create ordered route variant from selected published stops",
                      commands: [
                        {
                          resource: "route-variants",
                          id,
                          values: {
                            route_id: base.id,
                            name: variantName,
                            dataset_source: source,
                          },
                        },
                        ...members.map((stop) => ({
                          resource: "variant-stops",
                          values: {
                            variant_id: id,
                            stop_id: stop.id,
                            dataset_source: source,
                          },
                        })),
                      ],
                    },
                    token,
                  );
                  setBatch(result.data.id);
                } catch (exception) {
                  setError(errorText(exception));
                }
              }}
            >
              Create selected-stop variant draft
            </Button>
          </div>
        </div>
      )}
      <StationPicker
        label="Station to add"
        value={station}
        onChange={setStation}
      />
      <Button
        variant="secondary"
        disabled={!station}
        onClick={() => {
          if (station)
            setStops((old) => [
              ...old,
              {
                id: crypto.randomUUID(),
                station_id: station.id,
                name: station.name,
                offset_minutes: old.at(-1)?.offset_minutes || 0,
                distance_km: old.at(-1)?.distance_km || 0,
                boarding: false,
                alighting: false,
              },
            ]);
          setStation(undefined);
        }}
      >
        Add route stop
      </Button>
      <div className="table-scroll">
        <table>
          <thead>
            <tr>
              <th>Order / station</th>
              <th>Arrival elapsed minutes</th>
              <th>Departure elapsed minutes</th>
              <th>Distance km</th>
              <th>Permissions</th>
              <th>Reorder / remove</th>
            </tr>
          </thead>
          <tbody>
            {stops.map((s, index) => (
              <tr key={s.id}>
                <td>
                  {index + 1}. {s.name || s.station_id}
                </td>
                <td>
                  <input
                    aria-label={`Elapsed minutes stop ${index + 1}`}
                    type="number"
                    min="0"
                    value={s.offset_minutes}
                    onChange={(e) =>
                      setStops((old) =>
                        old.map((r) =>
                          r.id === s.id
                            ? {
                                ...r,
                                offset_minutes: Number(e.target.value),
                                arrival_offset_minutes: Number(e.target.value),
                              }
                            : r,
                        ),
                      )
                    }
                  />
                </td>
                <td>
                  <input
                    aria-label={`Departure elapsed minutes stop ${index + 1}`}
                    type="number"
                    min="0"
                    value={s.departure_offset_minutes ?? s.offset_minutes}
                    onChange={(e) =>
                      setStops((old) =>
                        old.map((r) =>
                          r.id === s.id
                            ? {
                                ...r,
                                departure_offset_minutes: Number(
                                  e.target.value,
                                ),
                              }
                            : r,
                        ),
                      )
                    }
                  />
                </td>
                <td>
                  <input
                    aria-label={`Distance stop ${index + 1}`}
                    type="number"
                    min="0"
                    step="0.01"
                    value={s.distance_km}
                    onChange={(e) =>
                      setStops((old) =>
                        old.map((r) =>
                          r.id === s.id
                            ? { ...r, distance_km: e.target.value }
                            : r,
                        ),
                      )
                    }
                  />
                </td>
                <td>
                  <label>
                    <input
                      type="checkbox"
                      checked={s.boarding}
                      onChange={(e) =>
                        setStops((old) =>
                          old.map((r) =>
                            r.id === s.id
                              ? { ...r, boarding: e.target.checked }
                              : r,
                          ),
                        )
                      }
                    />{" "}
                    Boarding
                  </label>
                  <label>
                    <input
                      type="checkbox"
                      checked={s.alighting}
                      onChange={(e) =>
                        setStops((old) =>
                          old.map((r) =>
                            r.id === s.id
                              ? { ...r, alighting: e.target.checked }
                              : r,
                          ),
                        )
                      }
                    />{" "}
                    Alighting
                  </label>
                </td>
                <td>
                  <Button
                    variant="ghost"
                    aria-label={`Move stop ${index + 1} up`}
                    disabled={!index}
                    onClick={() => move(index, -1)}
                  >
                    Up
                  </Button>
                  <Button
                    variant="ghost"
                    aria-label={`Move stop ${index + 1} down`}
                    disabled={index === stops.length - 1}
                    onClick={() => move(index, 1)}
                  >
                    Down
                  </Button>
                  <Button
                    variant="ghost"
                    onClick={() => {
                      if (s.existing) setRemoved((old) => [...old, s]);
                      setStops((old) => old.filter((r) => r.id !== s.id));
                    }}
                  >
                    Remove stop
                  </Button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {error && <Notice error>{error}</Notice>}
      {batch && (
        <Notice>
          Unpublished route change saved.{" "}
          <a href={`/admin/imports?batch=${batch}`}>
            Validate ordered stops and review publication
          </a>
        </Notice>
      )}
      <Button
        disabled={save.isPending || !meta.data}
        onClick={() => save.mutate()}
      >
        Save route draft
      </Button>
    </section>
  );
}
