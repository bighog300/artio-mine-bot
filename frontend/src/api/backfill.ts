import {
  createBackfillSchedule,
  getBackfillCampaigns,
  getBackfillSchedules,
  type BackfillCampaign,
  type BackfillSchedule,
  type CreateBackfillScheduleInput,
} from "@/lib/api";

export type { BackfillCampaign, BackfillSchedule, CreateBackfillScheduleInput };

export const backfillApi = {
  getCampaigns: getBackfillCampaigns,
  getSchedules: getBackfillSchedules,
  createSchedule: createBackfillSchedule,
};
