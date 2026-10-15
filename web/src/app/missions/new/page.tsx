"use client";

import { useRouter } from "next/navigation";
import { MissionForm, emptyProfile } from "@/components/mission-form";
import { api } from "@/lib/api";

export default function NewMission() {
  const router = useRouter();
  return (
    <div className="container py-8">
      <h1 className="text-2xl font-semibold tracking-tight">Plan a mission</h1>
      <p className="mt-1 text-muted-foreground">Four short steps. You can change any answer later.</p>
      <div className="mt-6">
        <MissionForm
          initial={emptyProfile()}
          submitLabel="Create roadmap"
          onSubmit={async (p) => {
            const m = await api.createMission(p);
            router.push(`/missions/${m.id}`);
          }}
        />
      </div>
    </div>
  );
}
