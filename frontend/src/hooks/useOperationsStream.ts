import { useEffect, useState } from "react";
import { useQueryClient } from "@tanstack/react-query";

export function useOperationsStream(station: string) {
  const client = useQueryClient();
  const [connection, setConnection] = useState("Connecting");
  useEffect(() => {
    if (!station) return;
    let closed = false;
    let socket: WebSocket;
    let retry: ReturnType<typeof setTimeout>;
    let delay = 500;
    let lastMessage = Date.now();
    function connect() {
      let version = -1;
      socket = new WebSocket(
        `${location.protocol === "https:" ? "wss" : "ws"}://${location.host}/api/v1/operations/stream?station_id=${encodeURIComponent(station)}`,
      );
      socket.onopen = () => {
        lastMessage = Date.now();
        setConnection("Connected locally");
        delay = 500;
        void client.invalidateQueries({ queryKey: ["operations"] });
      };
      socket.onmessage = (event) => {
        lastMessage = Date.now();
        try {
          const update = JSON.parse(event.data);
          if (
            update.type === "INVALIDATE" &&
            Number.isInteger(update.version) &&
            update.version > version
          ) {
            version = update.version;
            void client.invalidateQueries({ queryKey: ["operations"] });
            void client.invalidateQueries({ queryKey: ["service"] });
            void client.invalidateQueries({ queryKey: ["bootstrap"] });
            void client.invalidateQueries({ queryKey: ["journeys"] });
            void client.invalidateQueries({ queryKey: ["enquiry"] });
          }
        } catch {
          setConnection("Invalid update; refresh manually");
        }
      };
      socket.onclose = () => {
        if (closed) return;
        setConnection("Disconnected · retrying; manual refresh available");
        retry = setTimeout(connect, delay);
        delay = Math.min(10000, delay * 2);
      };
      socket.onerror = () => socket.close();
    }
    const offline = () => {
      setConnection("Disconnected · retrying; manual refresh available");
      socket?.close();
    };
    const online = () => {
      clearTimeout(retry);
      if (socket) {
        socket.onclose = null;
        socket.close();
      }
      connect();
    };
    window.addEventListener("offline", offline);
    window.addEventListener("online", online);
    const heartbeat = setInterval(() => {
      if (Date.now() - lastMessage > 10000) socket?.close();
    }, 5000);
    connect();
    return () => {
      closed = true;
      clearTimeout(retry);
      clearInterval(heartbeat);
      window.removeEventListener("offline", offline);
      window.removeEventListener("online", online);
      socket?.close();
    };
  }, [station, client]);
  return connection;
}
