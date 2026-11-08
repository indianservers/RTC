import { useEffect, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { api } from "./api";
/** Static reference metadata can remain cached; expired operational claims cannot. */
export function useFreshService(
  id: string | undefined,
  date: string,
  poll = true,
) {
  const query = useQuery({
    queryKey: ["service", id, date],
    queryFn: ({ signal }) =>
      api(`/app/services/${encodeURIComponent(id!)}?travel_date=${date}`, {
        signal,
      }),
    enabled: !!id,
    staleTime: 0,
    gcTime: 60000,
    refetchOnMount: poll ? "always" : false,
    refetchInterval: poll ? 15000 : false,
  });
  const expiry = query.data?.data.operational_expires_at;
  const [clock, setClock] = useState(Date.now());
  useEffect(() => {
    setClock(Date.now());
    if (!expiry) return;
    const timer = setTimeout(
      () => setClock(Date.now()),
      Math.max(0, Date.parse(expiry) - Date.now() + 5),
    );
    return () => clearTimeout(timer);
  }, [expiry, query.dataUpdatedAt]);
  const stale = !!query.error || (!!expiry && clock >= Date.parse(expiry));
  const raw = query.data?.data;
  const data =
    raw && stale
      ? {
          ...raw,
          status: {
            status: "STALE",
            gps_status: "STALE",
            delay_status: "UNKNOWN",
            delay_minutes: null,
            last_verified_at: raw.status.last_verified_at,
          },
          platform: { status: "stale", bay: null },
        }
      : raw;
  return {
    ...query,
    data: query.data ? { ...query.data, data } : undefined,
    operationalStale: stale,
  };
}
