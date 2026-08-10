"use client";

import { useEffect, useRef, useState } from "react";

import { paymentEventsUrl, type DecisionStep } from "./treasury";

const maxReconnects = 3;
const eventNames = ["primary", "critic", "final", "status"] as const;
const terminalStatuses = new Set(["APPROVED", "REVIEW", "REJECT", "PAUSE", "CONFIRMING", "CONFIRMED", "FAILED", "EXECUTION_BLOCKED"]);

export type SseEvent = {
  id?: string;
  event: string;
  data: unknown;
};

export function buildDecisionSteps(events: SseEvent[]): DecisionStep[] {
  const steps: DecisionStep[] = [];
  for (const event of events) {
    if (["primary", "critic", "final"].includes(event.event)) {
      const step = event.data as DecisionStep;
      const existing = steps.findIndex((item) => item.actor === step.actor);
      if (existing >= 0) {
        steps[existing] = step;
      } else {
        steps.push(step);
      }
    }
  }
  return steps;
}

export function usePaymentEvents(requestId?: string) {
  const [events, setEvents] = useState<SseEvent[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [connected, setConnected] = useState(false);
  // The request the current `events` array belongs to. State updates are
  // async, so on a requestId change callers can use this to avoid reading a
  // stale `events` snapshot from the previous request before it is cleared.
  const [eventsRequestId, setEventsRequestId] = useState<string | undefined>(undefined);
  const lastEventIdRef = useRef<string | undefined>(undefined);

  useEffect(() => {
    if (!requestId) return;

    let cancelled = false;
    let reconnects = 0;
    let source: EventSource | null = null;
    let retryTimer: ReturnType<typeof setTimeout> | null = null;
    let completed = false;

    setEvents([]);
    setEventsRequestId(requestId);
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
          const data = JSON.parse(message.data) as unknown;
          setEvents((current) => [
            ...current,
            { id: message.lastEventId || undefined, event: name, data }
          ]);
          if (name === "status" && isTerminalStatus(data)) {
            completed = true;
            source?.close();
            setConnected(false);
          }
        });
      }
      source.onerror = () => {
        source?.close();
        setConnected(false);
        if (completed || cancelled) return;
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

  return { events, eventsRequestId, error, connected, lastEventId: lastEventIdRef.current };
}

function isTerminalStatus(data: unknown): boolean {
  if (!data || typeof data !== "object" || !("status" in data)) return false;
  const status = String((data as { status: unknown }).status);
  return terminalStatuses.has(status);
}
