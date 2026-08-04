-- Migration: Add Additional Token Usage Columns
-- Description: Adds reasoning tokens and cached input tokens for comprehensive usage tracking
-- Requirements: Enhanced logging for all token usage metrics provided by LLM SDKs

-- Add additional token usage columns
ALTER TABLE agent_executions
ADD COLUMN reasoning_tokens INTEGER,
ADD COLUMN cached_input_tokens INTEGER;

-- Create indexes for token analysis
CREATE INDEX idx_agent_executions_reasoning_tokens ON agent_executions(reasoning_tokens) WHERE reasoning_tokens IS NOT NULL;
CREATE INDEX idx_agent_executions_cached_input_tokens ON agent_executions(cached_input_tokens) WHERE cached_input_tokens IS NOT NULL;

-- Add comments for documentation
COMMENT ON COLUMN agent_executions.reasoning_tokens IS 'Number of reasoning tokens used (e.g., for o1 models)';
COMMENT ON COLUMN agent_executions.cached_input_tokens IS 'Number of cached input tokens (for prompt caching)';