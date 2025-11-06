-- Migration: Add Input/Output Token Columns to Agent Executions
-- Description: Separates token usage into input and output tokens for better tracking
-- Requirements: Enhanced logging for token usage analysis

-- Add separate token columns
ALTER TABLE agent_executions
ADD COLUMN input_tokens INTEGER,
ADD COLUMN output_tokens INTEGER;

-- Create indexes for token analysis
CREATE INDEX idx_agent_executions_input_tokens ON agent_executions(input_tokens) WHERE input_tokens IS NOT NULL;
CREATE INDEX idx_agent_executions_output_tokens ON agent_executions(output_tokens) WHERE output_tokens IS NOT NULL;

-- Add comments for documentation
COMMENT ON COLUMN agent_executions.input_tokens IS 'Number of tokens in the input prompt';
COMMENT ON COLUMN agent_executions.output_tokens IS 'Number of tokens in the LLM response';
COMMENT ON COLUMN agent_executions.tokens_used IS 'Total tokens used (input + output)';