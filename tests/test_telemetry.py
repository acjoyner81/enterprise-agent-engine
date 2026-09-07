import json
import logging
import sys
from src.telemetry.logger import configure_telemetry_logger, get_logger, log_llm_execution, current_correlation_id

def test_structured_json_logging(capsys):
    configure_telemetry_logger("INFO")
    logger = get_logger("test-agent")
    
    current_correlation_id.set("corr-test-999")
    log_llm_execution(
        logger,
        correlation_id="corr-test-999",
        agent_name="TestAgent",
        prompt_tokens=42,
        completion_tokens=18,
        execution_time_ms=120.5,
        model_name="test-model",
        status="SUCCESS",
        cost_usd=0.0004
    )
    
    captured = capsys.readouterr()
    all_output = captured.out + captured.err
    log_lines = [line for line in all_output.splitlines() if "llm_call_completed" in line]
    assert len(log_lines) >= 1
    log_json = json.loads(log_lines[0])
    
    assert log_json["correlation_id"] == "corr-test-999"
    assert log_json["agent_name"] == "TestAgent"
    assert log_json["prompt_tokens"] == 42
    assert log_json["completion_tokens"] == 18
    assert log_json["total_tokens"] == 60
    assert log_json["execution_time_ms"] == 120.5
    assert log_json["model_name"] == "test-model"
    assert "timestamp" in log_json
