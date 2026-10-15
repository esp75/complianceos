"use client";

import { useRouter } from "next/navigation";
import { ApiNotice } from "@/components/api-notice";
import { MissionForm } from "@/components/mission-form";
import { api, paths, useApi } from "@/lib/api";
import type { Mission } from "@/lib/types";

export default function EditMission({ params }: { params: { id: string } }) {
  const router = useRouter();
  const mission = useApi<Mission>(paths.mission(params.id));
  return (
    <div className="container py-8">
      <h1 className="text-2xl font-semibold tracking-tight">Edit mission</h1>
      <ApiNotice error={mission.error} />
      {mission.data ? (
        <div className="mt-6">
          <MissionForm
            initial={mission.data.profile}
            submitLabel="Save changes"
            onSubmit={async (p) => {
              await api.updateMission(params.id, p);
              router.push(`/missions/${params.id}`);
            }}
          />
        </div>
      ) : null}
    </div>
  );
}
