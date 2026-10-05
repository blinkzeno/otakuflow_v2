import { useEffect, useState } from "react";
import { listJobs } from "../services/api.ts";
import type { Job } from "../types/index.ts";

const ACTIVE = new Set(["queued", "running"]);

/** Polls the project jobs every second. Stops at terminal states. */
export function useJobsPolling(projectId: number | null) {
  const [jobs, setJobs] = useState<Job[]>([]);

  useEffect(() => {
    if (projectId === null) return;
    let alive = true;
    let timer: number | undefined;

    async function load(): Promise<void> {
      try {
        const list = await listJobs(projectId as number);
        if (!alive) return;
        setJobs(list);
        if (!list.some((job) => ACTIVE.has(job.status))) stop();
      } catch {
        // keep old state, retry on next tick
      }
    }

    function stop(): void {
      if (timer !== undefined) {
        window.clearInterval(timer);
        timer = undefined;
      }
    }

    function start(): void {
      stop();
      void load();
      timer = window.setInterval(() => void load(), 1000);
    }

    function onVisible(): void {
      if (document.hidden) stop();
      else start();
    }

    start();
    document.addEventListener("visibilitychange", onVisible);
    return () => {
      alive = false;
      stop();
      document.removeEventListener("visibilitychange", onVisible);
    };
  }, [projectId]);

  return { jobs };
}
