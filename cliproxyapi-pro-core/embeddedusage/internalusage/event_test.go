package internalusage

import (
	"strings"
	"testing"
)

func TestNormalizeRawExtractsDiagnosticsAndRedactsSecrets(t *testing.T) {
	event, err := NormalizeRaw([]byte(`{
		"timestamp":"2026-06-13T00:00:00Z",
		"request_id":"req-1",
		"endpoint":"POST /v1/chat/completions",
		"model":"gpt-test",
		"api_key":"sk-secret",
		"latency_ms":1234,
		"ttft_ms":321,
		"reasoning_effort":"high",
		"service_tier":"priority",
		"failed":true,
		"fail":{"status_code":429,"code":"rate_limit","body":"{\"error\":{\"message\":\"too many requests\"}}"},
		"response_headers":{"set_cookie":"secret-cookie"}
	}`))
	if err != nil {
		t.Fatalf("NormalizeRaw() error = %v", err)
	}
	if event.TTFTMS == nil || *event.TTFTMS != 321 || event.StatusCode == nil || *event.StatusCode != 429 {
		t.Fatalf("diagnostics = ttft:%v status:%v, want 321/429", event.TTFTMS, event.StatusCode)
	}
	if event.ErrorCode != "rate_limit" || event.ErrorMessage != "too many requests" {
		t.Fatalf("error fields = %q/%q, want rate_limit/too many requests", event.ErrorCode, event.ErrorMessage)
	}
	if event.ReasoningEffort != "high" || event.ServiceTier != "priority" {
		t.Fatalf("tier fields = %q/%q, want high/priority", event.ReasoningEffort, event.ServiceTier)
	}
	if strings.Contains(event.RawJSON, "secret-cookie") || strings.Contains(event.RawJSON, "sk-secret") {
		t.Fatalf("RawJSON was not redacted: %s", event.RawJSON)
	}
}
