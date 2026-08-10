"use client";

import { useEffect, useRef, useState } from "react";

import { paymentEventsUrl } from "./treasury";

const maxReconnects = 3;
const eventNames = ["primary", "critic", "final", "status"] as const;

export type SseEvent = {
  id?: string;
  event: string;
  data: unknown;
};

export function usePaymentEvents(requestId?: string) {
  const [events, setEvents] = useState<SseEvent[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [connected, setConnected] = useState(false);
  const lastEventIdRef = useRef<string | undefined>(undefined);

  useEffect(() => {
    if (!requestId) return;

    let cancelled = false;
    let reconnects = 0;
    let source: EventSource | null = null;
    let retryTimer: ReturnType<typeof setTimeout> | null = null;

    setEvents([]);
    setError(null);
    lastEventIdRef.current = undefined;

    const connect = () => {
      if (cancelled) return;
      source = new EventSource(paymentEventsUrl(requestId, lastEventIdRef.current));
      source.onopen = () => {
        reconnects = 0;
        setConnected(true);
        setError(null);
      };
      source.addEventListener("heartbeat", () => {
        setConnected(true);
      });
      for (const name of eventNames) {
        source.addEventListener(name, (message: MessageEvent<string>) => {
          if (message.lastEventId) lastEventIdRef.current = message.lastEventId;
          setEvents((current) => [
            ...current,
            { id: message.lastEventId || undefined, event: name, data: JSON.parse(message.data) }
          ]);
        });
      }
      source.onerror = () => {
        source?.close();
        setConnected(false);
        reconnects += 1;
        if (reconnects > maxReconnects) {
          setError("event stream disconnected");
          return;
        }
        retryTimer = setTimeout(connect, reconnects * 1000);
      };
    };

    connect();

    return () => {
      cancelled = true;
      if (retryTimer) clearTimeout(retryTimer);
      source?.close();
      setConnected(false);
    };
  }, [requestId]);

  return { events, error, connected, lastEventId: lastEventIdRef.current };
}
