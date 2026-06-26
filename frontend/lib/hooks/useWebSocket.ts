"use client";

import { useEffect, useRef, useState } from "react";
import { websocketUrl } from "@/lib/api/client";
import type { WebSocketMessage } from "@/lib/api/types";

export type WsStatus = "connecting" | "live" | "offline";

interface UseWebSocketOptions {
  onMessage?: (msg: WebSocketMessage) => void;
  maxEvents?: number;
}

export function useWebSocket({
  onMessage,
  maxEvents = 20,
}: UseWebSocketOptions = {}) {
  const [status, setStatus] = useState<WsStatus>("connecting");
  const [events, setEvents] = useState<WebSocketMessage[]>([]);
  const socketRef = useRef<WebSocket | null>(null);
  const onMessageRef = useRef(onMessage);

  useEffect(() => {
    onMessageRef.current = onMessage;
  }, [onMessage]);

  useEffect(() => {
    const socket = new WebSocket(websocketUrl());
    socketRef.current = socket;

    socket.onopen = () => setStatus("live");
    socket.onclose = () => setStatus("offline");
    socket.onerror = () => setStatus("offline");

    socket.onmessage = (event) => {
      try {
        const parsed = JSON.parse(event.data as string) as WebSocketMessage;
        setEvents((prev) => [parsed, ...prev].slice(0, maxEvents));
        onMessageRef.current?.(parsed);
      } catch {
        // malformed message — ignore
      }
    };

    return () => {
      socket.close();
    };
  }, [maxEvents]);

  return { status, events };
}
