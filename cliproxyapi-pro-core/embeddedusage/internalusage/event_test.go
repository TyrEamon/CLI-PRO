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
		"tokens":{"input_tokens":10,"output_tokens":20,"cache_read_tokens":7,"cache_creation_tokens":3},
		"latency_ms":1234,
		"ttft_ms":321,
		"reasoning_effort":"high",
		"service_tier":"priority",
		"failed":true,
		"fail":{"status_code":429,"body":"{\"error\":{\"message\":\"too many requests\"}}"},
		"response_headers":{"set_cookie":"secret-cookie"}
	}`))
	if err != nil {
		t.Fatalf("NormalizeRaw() error = %v", err)
	}
	if event.TTFTMS == nil || *event.TTFTMS != 321 || event.StatusCode == nil || *event.StatusCode != 429 {
		t.Fatalf("diagnostics = ttft:%v status:%v, want 321/429", event.TTFTMS, event.StatusCode)
	}
	if event.ErrorCode != "" || event.ErrorMessage != "too many requests" {
		t.Fatalf("error fields = %q/%q, want empty/too many requests", event.ErrorCode, event.ErrorMessage)
	}
	if event.ReasoningEffort != "high" || event.ServiceTier != "priority" {
		t.Fatalf("tier fields = %q/%q, want high/priority", event.ReasoningEffort, event.ServiceTier)
	}
	if event.CacheTokens != 10 || event.TotalTokens != 40 {
		t.Fatalf("cache/total tokens = %d/%d, want 10/40", event.CacheTokens, event.TotalTokens)
	}
	if strings.Contains(event.RawJSON, "secret-cookie") || strings.Contains(event.RawJSON, "sk-secret") {
		t.Fatalf("RawJSON was not redacted: %s", event.RawJSON)
	}
}

func TestNormalizeRawIgnoresLegacyAliases(t *testing.T) {
	event, err := NormalizeRaw([]byte(`{
		"timestamp":"2026-06-13T00:00:00Z",
		"requestId":"legacy-request",
		"api":"POST /legacy",
		"modelName":"legacy-model",
		"apiKey":"sk-secret",
		"latencyMs":1234,
		"statusCode":429,
		"failed":true,
		"tokens":{"inputTokens":10,"outputTokens":20,"cacheTokens":5}
	}`))
	if err != nil {
		t.Fatalf("NormalizeRaw() error = %v", err)
	}
	if event.RequestID != "" || event.Endpoint != "-" || event.Model != "-" {
		t.Fatalf("legacy aliases were accepted: request_id=%q endpoint=%q model=%q", event.RequestID, event.Endpoint, event.Model)
	}
	if event.LatencyMS != nil || event.StatusCode != nil || event.TotalTokens != 0 {
		t.Fatalf("legacy diagnostics were accepted: latency=%v status=%v total=%d", event.LatencyMS, event.StatusCode, event.TotalTokens)
	}
}
