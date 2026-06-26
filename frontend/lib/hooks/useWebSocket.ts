"use client";

import { useEffect, useRef, useState } from "react";
import { websocketUrl } from "@/lib/api/client";
import type { WebSocketMessage } from "@/lib/api/types";

export type WsStatus = "connecting" | "live" | "offline";

interface UseWebSocketOptions {
  onMessage?: (msg: WebSocketMessage) => void;
  maxEvents?: number;
}

const INITIAL_RECONNECT_DELAY_MS = 1000;
const MAX_RECONNECT_DELAY_MS = 30000;

export function useWebSocket({
  onMessage,
  maxEvents = 20,
}: UseWebSocketOptions = {}) {
  const [status, setStatus] = useState<WsStatus>("connecting");
  const [events, setEvents] = useState<WebSocketMessage[]>([]);
  const socketRef = useRef<WebSocket | null>(null);
  const reconnectTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const reconnectDelayRef = useRef(INITIAL_RECONNECT_DELAY_MS);
  const onMessageRef = useRef(onMessage);

  useEffect(() => {
    onMessageRef.current = onMessage;
  }, [onMessage]);

  useEffect(() => {
    let stopped = false;

    const clearReconnectTimer = () => {
      if (reconnectTimerRef.current) {
        clearTimeout(reconnectTimerRef.current);
        reconnectTimerRef.current = null;
      }
    };

    const scheduleReconnect = () => {
      if (stopped || reconnectTimerRef.current) return;
      setStatus("offline");
      const delay = reconnectDelayRef.current;
      reconnectDelayRef.current = Math.min(delay * 2, MAX_RECONNECT_DELAY_MS);
      reconnectTimerRef.current = setTimeout(() => {
        reconnectTimerRef.current = null;
        connect();
      }, delay);
    };

    const connect = () => {
      if (stopped) return;
      setStatus("connecting");
      const socket = new WebSocket(websocketUrl());
      socketRef.current = socket;

      socket.onopen = () => {
        reconnectDelayRef.current = INITIAL_RECONNECT_DELAY_MS;
        setStatus("live");
      };

      socket.onclose = () => {
        if (socketRef.current === socket) socketRef.current = null;
        scheduleReconnect();
      };

      socket.onerror = () => {
        setStatus("offline");
        socket.close();
      };

      socket.onmessage = (event) => {
        try {
          const parsed = JSON.parse(event.data as string) as WebSocketMessage;
          setEvents((prev) => [parsed, ...prev].slice(0, maxEvents));
          onMessageRef.current?.(parsed);
        } catch {
          // malformed message - ignore
        }
      };
    };

    connect();

    return () => {
      stopped = true;
      clearReconnectTimer();
      socketRef.current?.close();
      socketRef.current = null;
    };
  }, [maxEvents]);

  return { status, events };
}
