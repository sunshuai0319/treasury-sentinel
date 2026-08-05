"use client";

import { useEffect, useState } from "react";

import { paymentEventsUrl } from "./treasury";

export type SseEvent = {
  event: string;
  data: unknown;
};

export function usePaymentEvents(requestId?: string) {
  const [events, setEvents] = useState<SseEvent[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!requestId) return;
    const source = new EventSource(paymentEventsUrl(requestId));
    const eventNames = ["primary", "critic", "final", "status"];
    const listeners = eventNames.map((name) => {
      const listener = (message: MessageEvent<string>) => {
        setEvents((current) => [...current, { event: name, data: JSON.parse(message.data) }]);
      };
      source.addEventListener(name, listener);
      return [name, listener] as const;
    });
    source.onerror = () => setError("event stream disconnected");
    return () => {
      for (const [name, listener] of listeners) source.removeEventListener(name, listener);
      source.close();
    };
  }, [requestId]);

  return { events, error };
}
