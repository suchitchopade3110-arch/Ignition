-- Database initialization for Ignition dashboard features.
-- Run these statements in the Supabase SQL editor to create the required tables and types.

-- Custom enums for validation
CREATE TYPE review_status AS ENUM ('queued', 'running', 'paused', 'waiting_hitl', 'completed', 'failed', 'cancelled');
CREATE TYPE severity_level AS ENUM ('none', 'low', 'medium', 'high', 'critical', 'info', 'warning', 'danger', 'success');

-- Create repositories table
CREATE TABLE repositories (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    owner TEXT NOT NULL,
    language TEXT NOT NULL DEFAULT 'TypeScript',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL
);

-- Create repository_settings table
CREATE TABLE repository_settings (
    repo_id TEXT PRIMARY KEY REFERENCES repositories(id) ON DELETE CASCADE,
    enable_ai_review BOOLEAN NOT NULL DEFAULT TRUE,
    enable_auto_fix BOOLEAN NOT NULL DEFAULT FALSE,
    enable_hitl BOOLEAN NOT NULL DEFAULT TRUE,
    security_scan BOOLEAN NOT NULL DEFAULT TRUE,
    architecture_scan BOOLEAN NOT NULL DEFAULT TRUE,
    logic_scan BOOLEAN NOT NULL DEFAULT TRUE
);

-- Create reviews table
CREATE TABLE reviews (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    repo_full_name TEXT NOT NULL,
    pr_number INT NOT NULL,
    title TEXT NOT NULL,
    author TEXT NOT NULL,
    branch TEXT NOT NULL,
    commit_sha TEXT NOT NULL,
    status review_status NOT NULL DEFAULT 'queued',
    severity severity_level NOT NULL DEFAULT 'none',
    acs_score NUMERIC(5,2),
    findings_count INT NOT NULL DEFAULT 0,
    diff_text TEXT,
    verified_findings JSONB DEFAULT '[]'::jsonb,
    final_comment_markdown TEXT,
    autofix_posted INT DEFAULT 0,
    autofix_failed INT DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL,
    completed_at TIMESTAMP WITH TIME ZONE,
    duration TEXT,
    previous_acs_score NUMERIC(5,2),
    regression JSONB,
    agents JSONB DEFAULT '[]'::jsonb,
    diffs JSONB DEFAULT '[]'::jsonb,
    github_comment_preview TEXT
);
