=== EXTRACTING API ENDPOINTS ===

**Endpoints Found:**

82:@router.get("/preview")
129:@router.post("/campaigns")
193:@router.post("/campaigns/{campaign_id}/start")
223:@router.post("/campaigns/{campaign_id}/check-completion")
247:@router.get("/campaigns")
281:@router.get("/campaigns/{campaign_id}")
321:@router.post("/calculate-completeness")
349:@router.get("/schedules")
359:@router.post("/schedules")
382:@router.patch("/schedules/{schedule_id}")
415:@router.delete("/schedules/{schedule_id}")

**Function Signatures:**

53:def _schedule_to_dict(schedule: BackfillSchedule) -> dict[str, object]:
70:def _compute_next_run(cron_expression: str | None) -> datetime | None:
83:async def preview_backfill_candidates(
130:async def create_backfill_campaign(
194:async def start_backfill_campaign(
224:async def check_campaign_completion_endpoint(
248:async def list_backfill_campaigns(
282:async def get_backfill_campaign(
322:async def calculate_existing_completeness(
350:async def list_backfill_schedules(
360:async def create_backfill_schedule(
383:async def update_backfill_schedule(
416:async def delete_backfill_schedule(
