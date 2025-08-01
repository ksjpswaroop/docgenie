import { useEffect, useState } from "react";

export function useEventStream(jobId: string) {
  const [events, setEvents] = useState<any[]>([]);
  useEffect(() => {
    const ev = new EventSource(`/api/proxy/stream/${jobId}`); // set up a Next.js proxy
    ev.onmessage = (e) => setEvents((prev) => [...prev, JSON.parse(e.data)]);
    return () => ev.close();
  }, [jobId]);
  return events;
}
