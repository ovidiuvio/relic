// Background jobs: how a schedule reads, and a run's status as words and a dot.

/** A job's schedule in words: "Every 6 hours", "Daily at 03:00", "Weekly on Sun at 04:30". */
export function describeTrigger(job) {
  const info = job?.trigger_info;
  if (!info?.type) return job?.trigger || "Not scheduled";
  if (info.type === "interval") {
    const secs = info.seconds;
    if (secs == null) return info.repr || "Interval";
    const every = (n, unit) => `Every ${n === 1 ? "" : `${n} `}${unit}${n === 1 ? "" : "s"}`;
    if (secs >= 3600 && secs % 3600 === 0) return every(secs / 3600, "hour");
    if (secs >= 60 && secs % 60 === 0) return every(secs / 60, "minute");
    return every(secs, "second");
  }
  if (info.type === "cron") {
    const { hour, minute, day_of_week: dow, day } = info.fields || {};
    let at = "";
    if (hour && hour !== "*" && minute && minute !== "*") at = ` at ${String(hour).padStart(2, "0")}:${String(minute).padStart(2, "0")}`;
    else if (minute && minute !== "*") at = ` at minute ${minute}`;
    const anyDow = dow === undefined || dow === "*";
    const anyDay = day === undefined || day === "*";
    if (anyDow && anyDay) return `Daily${at}`;
    if (!anyDow) return `Weekly on ${dow.split("-").map((w) => w[0].toUpperCase() + w.slice(1)).join("–")}${at}`;
    return `Monthly on day ${day}${at}`;
  }
  if (info.type === "date") {
    if (!info.run_date) return "Once";
    const [d, t] = info.run_date.split("T");
    return `Once on ${d} at ${t.slice(0, 5)}`;
  }
  return info.repr || job.trigger || "Unknown";
}

/** { label, dot } for a run: dot is the design system's r-dot modifier. */
export function runStatus(run) {
  if (run.status === "running") return { label: "Running", dot: "r-dot-warning" };
  if (run.status === "success") return { label: "Succeeded", dot: "" };
  if (run.status === "failed") return { label: "Failed", dot: "r-dot-danger" };
  return { label: run.status || "Unknown", dot: "r-dot-idle" };
}
