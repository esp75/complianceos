import { CircleAlert } from "lucide-react";
import type { ApiError } from "@/lib/api";

/** Shown when the planner API can't be reached, with the fix rather than a stack trace. */
export function ApiNotice({ error }: { error: ApiError | undefined }) {
  if (!error) return null;
  const unreachable = error.status >= 500 || error.status === 0;
  return (
    <div role="alert" className="mt-8 flex gap-3 rounded-lg border border-warn/40 bg-warn-soft p-4 text-sm">
      <CircleAlert className="mt-0.5 size-4 shrink-0 text-warn" />
      <div>
        <p className="font-medium">{unreachable ? "The planner API isn't reachable." : error.message}</p>
        {unreachable ? (
          <p className="mt-1 text-muted-foreground">
            Start everything with <code className="font-mono">docker compose up</code> from the repository root, or run the API on
            port 8001 (<code className="font-mono">cd app && uv run uvicorn app.main:app --port 8001</code>).
          </p>
        ) : null}
      </div>
    </div>
  );
}
