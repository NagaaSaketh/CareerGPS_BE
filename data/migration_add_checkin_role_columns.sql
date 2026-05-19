-- Migration: Add target_role and task_hours to checkins table
-- Run this in your Supabase SQL Editor

ALTER TABLE checkins
ADD COLUMN IF NOT EXISTS target_role TEXT,
ADD COLUMN IF NOT EXISTS task_hours JSONB DEFAULT '{}';

-- Index for fast role-filtered lookups
CREATE INDEX IF NOT EXISTS idx_checkins_user_role ON checkins(user_id, target_role);

-- Backfill existing rows: infer target_role from the user's latest report
-- (Optional — safe to skip if you don't need historical data categorized)
-- UPDATE checkins c
-- SET target_role = (
--   SELECT target_role FROM reports r
--   WHERE r.user_id = c.user_id
--   ORDER BY r.created_at DESC LIMIT 1
-- )
-- WHERE c.target_role IS NULL;
