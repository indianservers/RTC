import {
  createContext,
  useContext,
  useEffect,
  useState,
  useRef,
  lazy,
  Suspense,
} from "react";
import { NavLink, Route, Routes, Link, useLocation } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import {
  BusFront,
  MessageSquareText,
  Map,
  Search,
  ShieldCheck,
  Menu,
  Wifi,
  ArrowUpRight,
  X,
} from "lucide-react";
import { api, type Bootstrap, type Station } from "./api";
import { Badge, Button } from "./components/ui";
import { ChatPage } from "./pages/ChatPage";
import { PlannerPage } from "./pages/PlannerPage";
import { ServicePage } from "./pages/ServicePage";
const AdminPage = lazy(() =>
  import("./pages/AdminPage").then((m) => ({ default: m.AdminPage })),
);
const OperationsBoard = lazy(() =>
  import("./pages/OperationsCenter").then((m) => ({
    default: m.OperationsCenter,
  })),
);
interface Workspace {
  station?: Station;
  setStation: (s?: Station) => void;
  operator: string;
  setOperator: (s: string) => void;
  bootstrap?: Bootstrap;
  online: boolean;
}
const Context = createContext<Workspace | null>(null);
export const useWorkspace = () => useContext(Context)!;
export function App() {
  const passengerHome = useLocation().pathname === "/";
  const [station, setStation] = useState<Station | undefined>(() => {
    try {
      return (
        JSON.parse(sessionStorage.getItem("rtc-stand") || "null") || undefined
      );
    } catch {
      return undefined;
    }
  });
  const [operator, setOperator] = useState(
    () => sessionStorage.getItem("rtc-operator") || "",
  );
  const [menu, setMenu] = useState(false);
  const [kiosk, setKiosk] = useState(
    () => sessionStorage.getItem("rtc-kiosk") === "true",
  );
  const initialized = useRef(!!station);
  useEffect(() => {
    if (station) sessionStorage.setItem("rtc-stand", JSON.stringify(station));
    sessionStorage.setItem("rtc-operator", operator);
  }, [station, operator]);
  const query = useQuery({
    queryKey: ["bootstrap"],
    queryFn: () =>
      api<{ data: Bootstrap & { default_station?: Station } }>(
        "/app/bootstrap",
      ),
    refetchInterval: 30000,
  });
  useEffect(() => {
    if (query.data?.data.default_station && !initialized.current) {
      initialized.current = true;
      setStation(query.data.data.default_station);
    }
  }, [query.data]);
  const selectedStation = useQuery({
    queryKey: ["station-label", station?.id],
    queryFn: ({ signal }) =>
      api(`/stations/resolve?value=${encodeURIComponent(station!.id)}`, {
        signal,
      }),
    enabled: !!station,
    staleTime: 30000,
    refetchInterval: 30000,
  });
  useEffect(() => {
    const candidate = selectedStation.data?.data?.candidates?.[0];
    if (candidate)
      setStation((previous) =>
        previous &&
        previous.id === candidate.id &&
        (previous.name !== candidate.name ||
          previous.code !== candidate.code ||
          previous.timezone !== candidate.timezone)
          ? candidate
          : previous,
      );
  }, [selectedStation.data]);
  const data = query.data?.data;
  const demo =
    !!data?.sources.length &&
    data.sources.every((s) => ["DEMO", "SYNTHETIC"].includes(s));
  return (
    <Context.Provider
      value={{
        station,
        setStation,
        operator,
        setOperator,
        bootstrap: data,
        online: query.isSuccess,
      }}
    >
      <a className="skip-link" href="#main-content">
        Skip to main content
      </a>
      <div
        className={`app-shell ${passengerHome ? "passenger-home" : ""} ${kiosk ? "kiosk-mode" : ""}`}
      >
        <aside className={`sidebar ${menu ? "open" : ""}`}>
          <Link to="/" className="brand" onClick={() => setMenu(false)}>
            <span>
              <BusFront size={24} />
            </span>
            <div>
              RTC <b>Smart Enquiry</b>
              <small>YOUR JOURNEY, SIMPLIFIED</small>
            </div>
          </Link>
          <p className="nav-caption">PASSENGER WORKSPACE</p>
          <nav aria-label="Main navigation">
            {[
              ["/", "Smart enquiry", MessageSquareText],
              ["/search", "Find a bus", Search],
              ["/journeys", "Journey planner", Map],
              ["/board", "Live station board", BusFront],
            ].map(([path, label, Icon]) => {
              const I = Icon as typeof Map;
              return (
                <NavLink
                  end={path === "/"}
                  key={String(path)}
                  to={String(path)}
                  onClick={() => setMenu(false)}
                >
                  <I size={19} />
                  {String(label)}
                </NavLink>
              );
            })}
          </nav>
          <div className="sidebar-bottom">
            <div className="local-note">
              <Wifi size={18} />
              <div>
                <strong>Locally connected</strong>
                <small>Information from your RTC database.</small>
              </div>
            </div>
            <NavLink to="/admin" onClick={() => setMenu(false)}>
              <ShieldCheck size={18} />
              Administration
              <ArrowUpRight size={14} />
            </NavLink>
            <p>
              Information service only.
              <br />
              No bookings or payments.
            </p>
          </div>
        </aside>
        {menu && (
          <button
            className="scrim"
            aria-label="Close navigation"
            onClick={() => setMenu(false)}
          />
        )}
        <div className="workspace">
          <header className="topbar">
            <Button
              variant="ghost"
              className="mobile-menu"
              aria-label="Toggle navigation"
              onClick={() => setMenu(!menu)}
            >
              {menu ? <X size={20} /> : <Menu size={20} />}
            </Button>
            <div className="breadcrumb">
              Passenger workspace <span>/</span>{" "}
              <strong>RTC information</strong>
            </div>
            <div className="top-status">
              <span
                className={
                  query.isSuccess ? "connection" : "connection disconnected"
                }
              >
                <i />
                {query.isSuccess
                  ? "Local backend connected"
                  : "Backend unavailable"}
              </span>
              <Badge tone={demo ? "amber" : "muted"}>
                {demo
                  ? "DEMO DATA"
                  : data
                    ? "LOCAL RECORDS"
                    : "DATA UNCONFIRMED"}
              </Badge>
              <button
                className="kiosk-toggle"
                aria-pressed={kiosk}
                aria-label="Kiosk touch mode"
                onClick={() => {
                  setKiosk(!kiosk);
                  sessionStorage.setItem("rtc-kiosk", String(!kiosk));
                }}
              >
                Kiosk {kiosk ? "on" : "off"}
              </button>
              <span className="language">EN</span>
            </div>
          </header>
          <main id="main-content">
            <Suspense
              fallback={
                <div className="empty" role="status">
                  Loading local application…
                </div>
              }
            >
              <Routes>
                <Route path="/" element={<ChatPage />} />
                <Route path="/search" element={<PlannerPage searchOnly />} />
                <Route path="/journeys" element={<PlannerPage />} />
                <Route path="/services/:id" element={<ServicePage />} />
                <Route path="/admin/*" element={<AdminPage />} />
                <Route path="/board" element={<OperationsBoard passenger />} />
                <Route
                  path="*"
                  element={
                    <div className="empty">
                      <h1>Page not found</h1>
                      <Link to="/">Return to enquiry</Link>
                    </div>
                  }
                />
              </Routes>
            </Suspense>
          </main>
          <footer className="app-footer">
            RTC Smart Enquiry{" "}
            <span>English text · Local database · No booking service</span>
          </footer>
        </div>
      </div>
    </Context.Provider>
  );
}
