-- Migration: Add selected_role to profiles table
-- Run this in your Supabase SQL Editor if you plan to use set_selected_role / get_selected_role

ALTER TABLE profiles
ADD COLUMN IF NOT EXISTS selected_role TEXT;

CREATE INDEX IF NOT EXISTS idx_profiles_selected_role ON profiles(selected_role);
