import { useRef, useState } from "react";

import { useMutation } from "@tanstack/react-query";

import { ArrowRight, ArrowLeftRight, Filter, Search } from "lucide-react";

import { useWorkspace } from "../App";

import {
  api,
  post,
  today,
  localTimestamp,
  errorText,
  type Station,
  type Row,
} from "../api";

import { StationPicker } from "../components/StationPicker";

import { FilterBar } from "../components/FilterBar";

import { JourneyComparison } from "../components/JourneyComparison";

import { LoadingSkeleton } from "../components/feedback";

import { JourneyCard } from "../components/JourneyCard";

import { BusCard } from "../components/BusCard";

import { Button, Empty, Notice, PageTitle } from "../components/ui";

export function PlannerPage({ searchOnly = false }: { searchOnly?: boolean }) {
  const workspace = useWorkspace();

  const [origin, setOrigin] = useState<Station>();

  const [originEdited, setOriginEdited] = useState(false);

  const [destination, setDestination] = useState<Station>();

  const [date, setDate] = useState(today());

  const [clock, setClock] = useState("00:00");

  const [before, setBefore] = useState("");

  const [deadline, setDeadline] = useState("");

  const [operator, setOperator] = useState("");

  const [category, setCategory] = useState("");

  const [ac, setAc] = useState("");

  const [sleeper, setSleeper] = useState("");

  const [budget, setBudget] = useState("");

  const [seats, setSeats] = useState(false);

  const [direct, setDirect] = useState(searchOnly);

  const [transfers, setTransfers] = useState(2);

  const [ranking, setRanking] = useState("EARLIEST_ARRIVAL");

  const [localError, setLocalError] = useState("");

  const [compareIds, setCompareIds] = useState<string[]>([]);

  const [comparison, setComparison] = useState<Row[] | null>(null);

  const [formChanged, setFormChanged] = useState(false);

  const searchController = useRef<AbortController | null>(null);

  const revision = useRef(0);

  const selectedOrigin = originEdited ? origin : workspace.station;

  function payload(mode = ranking) {
    if (!selectedOrigin || !destination)
      throw new Error(
        "Choose a unique source and destination from the station suggestions.",
      );

    if (selectedOrigin.id === destination.id)
      throw new Error("Choose a destination different from your source.");

    const zone = selectedOrigin.timezone;

    return {
      origin: selectedOrigin.id,

      destination: destination.id,

      earliest_departure: localTimestamp(date, clock, zone),

      latest_departure: before ? localTimestamp(date, before, zone) : undefined,

      arrival_deadline: deadline
        ? localTimestamp(deadline.slice(0, 10), deadline.slice(11, 16), zone)
        : undefined,

      max_transfers: direct ? 0 : transfers,

      horizon_hours: 48,

      ranking: mode,

      require_verified_seats: seats,

      filters: {
        operator: operator || undefined,

        category: category || undefined,

        ac: ac === "" ? undefined : ac === "true",

        sleeper: sleeper === "" ? undefined : sleeper === "true",

        max_fare: budget || undefined,
      },

      limit: 20,
    };
  }

  const search = useMutation({
    mutationFn: (input: { mode: string; query?: Row }) => {
      const controller = new AbortController();

      searchController.current = controller;

      return api("/journeys/search", {
        method: "POST",

        body: JSON.stringify(input.query || payload(input.mode)),

        signal: controller.signal,
      });
    },

    onSuccess: () => {
      setCompareIds([]);

      setComparison(null);

      setFormChanged(false);
    },

    onError: (e) => {
      if (!(e instanceof DOMException && e.name === "AbortError"))
        setLocalError(errorText(e));
    },
  });

  function submit(mode = ranking) {
    setLocalError("");

    search.mutate({ mode });
  }

  const compare = useMutation({
    mutationFn: async () => {
      const requestRevision = revision.current;

      setComparison(null);

      const fresh = await post("/journeys/compare", {
        ...search.data!.applied_filters,
      });

      const valid = fresh.itineraries.filter((j: Row) =>
        compareIds.includes(j.journey_id),
      );

      if (valid.length !== compareIds.length)
        throw new Error(
          "An option changed or is no longer eligible. Refresh the search before comparing.",
        );

      return { valid, requestRevision };
    },

    onSuccess: ({ valid, requestRevision }) => {
      if (requestRevision === revision.current) setComparison(valid);
    },

    onError: (e) => setLocalError(errorText(e)),
  });

  function resetSearch() {
    searchController.current?.abort();

    revision.current += 1;

    search.reset();
    compare.reset();

    setOrigin(undefined);
    setOriginEdited(false);
    setDestination(undefined);

    setDate(today());
    setClock("00:00");
    setBefore("");
    setDeadline("");

    setOperator("");
    setCategory("");
    setAc("");
    setSleeper("");
    setBudget("");

    setSeats(false);
    setDirect(searchOnly);
    setTransfers(2);
    setRanking("EARLIEST_ARRIVAL");

    setCompareIds([]);
    setComparison(null);
    setFormChanged(false);
    setLocalError("");
  }

  function recoverFilter(key: string) {
    const query = payload();

    query.filters = { ...query.filters, [key]: undefined };

    if (key === "ac") setAc("");

    if (key === "sleeper") setSleeper("");

    if (key === "max_fare") setBudget("");

    setCompareIds([]);
    setComparison(null);
    setLocalError("");

    search.mutate({ mode: ranking, query });
  }

  function toggleCompare(id: string) {
    setLocalError("");

    setComparison(null);

    setCompareIds((ids) =>
      ids.includes(id)
        ? ids.filter((x) => x !== id)
        : ids.length < 3
          ? [...ids, id]
          : ids,
    );
  }

  const names: Record<string, string> = {};

  if (selectedOrigin) names[selectedOrigin.id] = selectedOrigin.name;

  if (destination) names[destination.id] = destination.name;

  return (
    <div className="page-container">
      <PageTitle
        eyebrow="PLAN WITH CONFIDENCE"

        title={
          searchOnly ? "Find your next bus" : "Every leg, one clear journey"
        }

        description={
          searchOnly
            ? "Search actual local services and narrow down your options."
            : "Compare direct services and practical connections from local timetables."
        }
      />

      <form
        className="search-panel"

        onChange={() => {
          revision.current += 1;

          if (search.isPending) searchController.current?.abort();

          if (search.data || search.isPending) {
            setFormChanged(true);

            setCompareIds([]);

            setComparison(null);
          }
        }}

        onSubmit={(e) => {
          e.preventDefault();

          submit();
        }}
      >
        <div className="search-main">
          <StationPicker
            label="From"

            value={selectedOrigin}

            onChange={(s) => {
              setOriginEdited(true);

              setOrigin(s);
            }}

            required
          />

          <button
            type="button"

            className="swap"

            aria-label="Swap source and destination"

            onClick={() => {
              setOriginEdited(true);

              setOrigin(destination);

              setDestination(selectedOrigin);
            }}
          >
            <ArrowLeftRight size={18} />
          </button>

          <StationPicker
            label="To"

            value={destination}

            onChange={setDestination}

            required
          />

          <label className="field">
            Travel date
            <input
              type="date"

              required

              value={date}

              onChange={(e) => setDate(e.target.value)}
            />
          </label>

          <label className="field">
            Leave at or after
            <input
              type="time"

              required

              value={clock}

              onChange={(e) => setClock(e.target.value)}
            />
          </label>
        </div>

        <details className="advanced-filters">
          <summary>Preferences & arrival deadline</summary>{" "}
          <FilterBar className="filter-grid" label="Journey preferences">
            <label className="field">
              Operator
              <select
                value={operator}

                onChange={(e) => setOperator(e.target.value)}
              >
                <option value="">All operators</option>

                {workspace.bootstrap?.operators.map((op) => (
                  <option value={op.code} key={op.id}>
                    {op.name}
                  </option>
                ))}
              </select>
            </label>

            <label className="field">
              Bus category
              <select
                value={category}

                onChange={(e) => setCategory(e.target.value)}
              >
                <option value="">All categories</option>

                {workspace.bootstrap?.categories.map((c) => (
                  <option key={c.id} value={c.id}>
                    {c.name}
                  </option>
                ))}
              </select>
            </label>

            <label className="field">
              Air conditioning
              <select value={ac} onChange={(e) => setAc(e.target.value)}>
                <option value="">Any</option>

                <option value="true">AC only</option>

                <option value="false">Non-AC only</option>
              </select>
            </label>

            <label className="field">
              Configuration
              <select
                value={sleeper}

                onChange={(e) => setSleeper(e.target.value)}
              >
                <option value="">Any</option>

                <option value="true">Sleeper only</option>

                <option value="false">Seater only</option>
              </select>
            </label>

            <label className="field">
              Fare ceiling (INR)
              <input
                type="number"

                min="0"

                step="0.01"

                value={budget}

                placeholder="No limit"

                onChange={(e) => setBudget(e.target.value)}
              />
            </label>

            <label className="field">
              Maximum transfers
              <select
                value={direct ? 0 : transfers}

                disabled={direct}

                onChange={(e) => setTransfers(Number(e.target.value))}
              >
                <option value={0}>No transfers</option>

                <option value={1}>One transfer</option>

                <option value={2}>Two transfers</option>
              </select>
            </label>

            <label className="field">
              Leave before (optional)
              <input
                type="time"

                value={before}

                onChange={(e) => setBefore(e.target.value)}
              />
            </label>

            <label className="field">
              Arrive by (optional)
              <input
                type="datetime-local"

                value={deadline}

                onChange={(e) => setDeadline(e.target.value)}
              />
            </label>
          </FilterBar>
        </details>

        <div className="search-bottom">
          <div className="checkboxes">
            <label>
              <input
                type="checkbox"

                checked={direct}

                onChange={(e) => setDirect(e.target.checked)}
              />
              Direct buses only
            </label>

            <label>
              <input
                type="checkbox"

                checked={seats}

                onChange={(e) => setSeats(e.target.checked)}
              />
              Require verified seat availability
            </label>
          </div>

          <Button type="button" variant="ghost" onClick={resetSearch}>
            Reset search
          </Button>

          <Button type="submit" disabled={search.isPending}>
            <Search size={16} />

            {search.isPending ? "Searching…" : "Search journeys"}

            <ArrowRight size={16} />
          </Button>
        </div>
      </form>

      {localError && <Notice error>{localError}</Notice>}

      <div className="results-heading">
        <div>
          <span className="eyebrow">YOUR OPTIONS</span>

          <h2>
            {search.data
              ? `${search.data.itineraries.length} matching journey(s)`
              : "Find the journey that fits"}
          </h2>
        </div>

        <div className="segmented" role="group" aria-label="Rank journeys">
          {[
            ["EARLIEST_ARRIVAL", "Fastest arrival"],

            ["LOWEST_FARE", "Cheapest known fare"],

            ["FEWEST_TRANSFERS", "Fewest transfers"],

            ["SHORTEST_DURATION", "Shortest duration"],
          ].map(([mode, label]) => (
            <button
              key={mode}

              className={mode === ranking ? "active" : ""}

              disabled={search.isPending || formChanged}

              onClick={() => {
                setRanking(mode);

                if (search.data) submit(mode);
              }}
            >
              {label}
            </button>
          ))}
        </div>
      </div>

      {formChanged && (
        <Notice>
          Filters changed. Search again to update these results; comparison is
          disabled until then.
        </Notice>
      )}

      {search.data && search.data.itineraries.length > 0 && (
        <div className="comparison-toolbar">
          <span>
            Select two or three options to compare. A new search clears
            selection.
          </span>

          <Button
            variant="secondary"

            disabled={
              compareIds.length < 2 ||
              search.isPending ||
              compare.isPending ||
              formChanged
            }

            onClick={() => compare.mutate()}
          >
            {compare.isPending
              ? "Validating options…"
              : `Compare journeys (${compareIds.length})`}
          </Button>
        </div>
      )}

      {comparison && (
        <JourneyComparison
          journeys={comparison}

          onClose={() => setComparison(null)}
        />
      )}

      {search.data?.comparisons?.map((line: string) => (
        <p key={line} className="subtle">
          {line}
        </p>
      ))}

      {search.isPending ? (
        <LoadingSkeleton label="Searching local journeys…" />
      ) : !search.data ? (
        <Empty title="A little planning goes a long way">
          Choose your destination and search. Every result comes from the local
          RTC database.
        </Empty>
      ) : !search.data.itineraries.length ? (
        <Empty title={direct ? "No direct bus found" : "No matching journeys"}>
          No eligible route was found for {selectedOrigin?.name} to{" "}
          {destination?.name} from {date} at {clock}. Your restrictions are
          retained. Change the date or choose a specific filter to remove.
          {!formChanged && (
            <div className="followups" aria-label="Search recovery actions">
              {ac && (
                <Button variant="secondary" onClick={() => recoverFilter("ac")}>
                  Remove AC restriction
                </Button>
              )}

              {sleeper && (
                <Button
                  variant="secondary"
                  onClick={() => recoverFilter("sleeper")}
                >
                  Remove sleeper restriction
                </Button>
              )}

              {budget && (
                <Button
                  variant="secondary"
                  onClick={() => recoverFilter("max_fare")}
                >
                  Remove fare ceiling
                </Button>
              )}
            </div>
          )}
          {direct && !formChanged && (
            <Button
              variant="secondary"

              onClick={() => {
                const query = { ...payload(), max_transfers: 1 };

                setDirect(false);

                setTransfers(1);

                search.mutate({ mode: ranking, query });
              }}
            >
              Search with up to one transfer (keep other filters)
            </Button>
          )}
        </Empty>
      ) : (
        <div className="journey-results">
          {search.data.itineraries.map((journey: Row, index: number) => (
            <div key={journey.journey_id} className="journey-option">
              <label className="compare-select">
                <input
                  type="checkbox"

                  aria-label={`Compare option ${index + 1}`}

                  checked={compareIds.includes(journey.journey_id)}

                  disabled={
                    formChanged ||
                    compare.isPending ||
                    (!compareIds.includes(journey.journey_id) &&
                      compareIds.length >= 3)
                  }

                  onChange={() => toggleCompare(journey.journey_id)}
                />
                Option {index + 1} · Add to comparison
              </label>

              <p className="subtle">
                Qualifies for submitted filters ·{" "}
                {journey.legs.length === 1
                  ? "Direct service"
                  : `${journey.legs.length - 1} transfer(s)`}{" "}
                ·{" "}
                {journey.total_fare == null
                  ? "Total fare unconfirmed"
                  : "Known fare"}
              </p>

              {searchOnly && journey.legs.length === 1 ? (
                <BusCard
                  row={{
                    ...journey.legs[0],

                    departure: journey.departure_at,

                    arrival: journey.arrival_at,

                    dataset_source: journey.legs[0].source,
                  }}
                />
              ) : (
                <JourneyCard journey={journey} stationNames={names} />
              )}
            </div>
          ))}
        </div>
      )}

      {search.data && (
        <div className="pagination">
          <Button
            variant="secondary"

            disabled={
              search.isPending || formChanged || !search.data.pagination.offset
            }

            onClick={() =>
              search.mutate({
                mode: ranking,

                query: {
                  ...search.data!.applied_filters,

                  offset: Math.max(0, search.data!.pagination.offset - 20),
                },
              })
            }
          >
            Previous journeys
          </Button>

          <span>
            {search.data.pagination.offset + 1}–
            {search.data.pagination.offset + search.data.itineraries.length} of{" "}
            {search.data.pagination.eligible_count} eligible within search
            bounds
          </span>

          <Button
            variant="secondary"

            disabled={
              search.isPending ||
              formChanged ||
              search.data.pagination.offset + 20 >=
                search.data.pagination.eligible_count
            }

            onClick={() =>
              search.mutate({
                mode: ranking,

                query: {
                  ...search.data!.applied_filters,

                  offset: search.data!.pagination.offset + 20,
                },
              })
            }
          >
            Next journeys
          </Button>
        </div>
      )}

      {search.data && (
        <details className="source-details">
          <summary>
            <Filter size={14} />
            Search bounds & data notes
          </summary>

          <p>
            Horizon ends {search.data.search_horizon_end}.{" "}
            {search.data.search_stats.candidate_connections} candidate
            connections checked.
          </p>

          {search.data.warnings.map((w: string) => (
            <p key={w}>{w}</p>
          ))}
        </details>
      )}
    </div>
  );
}
