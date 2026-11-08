import { useEffect, useId, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { MapPin } from "lucide-react";
import { api, type Station } from "../api";
export function StationPicker({
  label,
  value,
  onChange,
  required = false,
  disabled = false,
}: {
  label: string;
  value?: Station;
  onChange: (station?: Station) => void;
  required?: boolean;
  disabled?: boolean;
}) {
  const id = useId();
  const [text, setText] = useState(value?.name || "");
  const [search, setSearch] = useState("");
  const [open, setOpen] = useState(false);
  const [active, setActive] = useState(0);
  useEffect(() => {
    if (value) setText(value.name);
  }, [value]);
  useEffect(() => {
    const timer = setTimeout(() => setSearch(text), 180);
    return () => clearTimeout(timer);
  }, [text]);
  const query = useQuery({
    queryKey: ["station-search", search],
    queryFn: ({ signal }) =>
      api<{ data: Station[] }>(
        `/stations/search?q=${encodeURIComponent(search)}`,
        { signal },
      ),
    enabled: open && search.trim().length > 0,
  });
  const pendingInput = text !== search;
  const options = pendingInput ? [] : query.data?.data || [];
  function select(station: Station) {
    onChange(station);
    setText(station.name);
    setOpen(false);
    setActive(0);
  }
  return (
    <div className="field station-picker">
      <label htmlFor={id}>{label}</label>
      <div className="input-icon">
        <MapPin size={16} />
        <input
          id={id}
          role="combobox"
          autoComplete="off"
          aria-autocomplete="list"
          aria-expanded={open}
          aria-controls={`${id}-options`}
          aria-activedescendant={
            open && options[active] ? `${id}-${active}` : undefined
          }
          required={required}
          disabled={disabled}
          value={text}
          placeholder="Search a station or alias"
          onFocus={() => setOpen(true)}
          onBlur={() => setOpen(false)}
          onChange={(e) => {
            setText(e.target.value);
            onChange(undefined);
            setOpen(true);
            setActive(0);
          }}
          onKeyDown={(e) => {
            if (e.key === "ArrowDown") {
              e.preventDefault();
              setOpen(true);
              setActive((n) =>
                Math.min(n + 1, Math.max(0, options.length - 1)),
              );
            }
            if (e.key === "ArrowUp") {
              e.preventDefault();
              setActive((n) => Math.max(0, n - 1));
            }
            if (e.key === "Enter" && open && options[active]) {
              e.preventDefault();
              select(options[active]);
            }
            if (e.key === "Escape") setOpen(false);
          }}
        />
      </div>
      {open && text && (
        <div className="station-options" id={`${id}-options`} role="listbox">
          {query.isFetching || pendingInput ? (
            <p>Searching local stations…</p>
          ) : options.length ? (
            options.map((station, i) => (
              <button
                type="button"
                role="option"
                aria-selected={active === i}
                id={`${id}-${i}`}
                key={station.id}
                onMouseDown={(e) => e.preventDefault()}
                onClick={() => select(station)}
              >
                <span>{station.name}</span>
                <small>{station.code}</small>
              </button>
            ))
          ) : (
            <p>
              {query.error
                ? "Station search unavailable."
                : "No matching station. Try another name."}
            </p>
          )}
        </div>
      )}
    </div>
  );
}
