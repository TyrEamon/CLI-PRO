package embeddedusage

import (
	"bufio"
	"context"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"strconv"
	"strings"
	"time"

	"github.com/gin-gonic/gin"
	"github.com/router-for-me/CLIProxyAPI/v6/internal/embeddedusage/internalusage"
)

const (
	accountInspectionScheduleExportRecordType = "account_inspection_schedule"
	liteLLMModelPricesURL                     = "https://raw.githubusercontent.com/BerriAI/litellm/main/model_prices_and_context_window.json"
)

type accountInspectionScheduleExportRecord struct {
	RecordType string          `json:"record_type"`
	Version    int             `json:"version"`
	Schedule   json.RawMessage `json:"schedule"`
	ExportedAt int64           `json:"exported_at_ms"`
}

type usageStatsProvider interface {
	Stats() ServiceStats
}

type Server struct {
	cfg           Config
	store         *Store
	statsProvider usageStatsProvider
}

func NewServer(cfg Config, store *Store, statsProvider usageStatsProvider) *Server {
	return &Server{cfg: cfg, store: store, statsProvider: statsProvider}
}

func RegisterGinRoutes(group *gin.RouterGroup) {
	server := defaultServer()
	if server == nil {
		group.GET("", func(c *gin.Context) {
			c.JSON(http.StatusServiceUnavailable, gin.H{"error": "usage service is not available"})
		})
		group.GET("/export", func(c *gin.Context) {
			c.JSON(http.StatusServiceUnavailable, gin.H{"error": "usage service is not available"})
		})
		group.POST("/import", func(c *gin.Context) {
			c.JSON(http.StatusServiceUnavailable, gin.H{"error": "usage service is not available"})
		})
		group.GET("/status", func(c *gin.Context) {
			c.JSON(http.StatusServiceUnavailable, gin.H{"error": "usage service is not available"})
		})
		group.GET("/dead-letters", func(c *gin.Context) {
			c.JSON(http.StatusServiceUnavailable, gin.H{"error": "usage service is not available"})
		})
		group.GET("/dead-letters/export", func(c *gin.Context) {
			c.JSON(http.StatusServiceUnavailable, gin.H{"error": "usage service is not available"})
		})
		group.GET("/quota-cache", func(c *gin.Context) {
			c.JSON(http.StatusServiceUnavailable, gin.H{"error": "usage service is not available"})
		})
		group.PUT("/quota-cache", func(c *gin.Context) {
			c.JSON(http.StatusServiceUnavailable, gin.H{"error": "usage service is not available"})
		})
		group.DELETE("/quota-cache", func(c *gin.Context) {
			c.JSON(http.StatusServiceUnavailable, gin.H{"error": "usage service is not available"})
		})
		group.GET("/model-prices", func(c *gin.Context) {
			c.JSON(http.StatusServiceUnavailable, gin.H{"error": "usage service is not available"})
		})
		group.PUT("/model-prices", func(c *gin.Context) {
			c.JSON(http.StatusServiceUnavailable, gin.H{"error": "usage service is not available"})
		})
		group.POST("/model-prices/sync", func(c *gin.Context) {
			c.JSON(http.StatusServiceUnavailable, gin.H{"error": "usage service is not available"})
		})
		return
	}
	server.RegisterGinRoutes(group)
}

func (s *Server) RegisterGinRoutes(group *gin.RouterGroup) {
	group.GET("", s.handleUsage)
	group.GET("/export", s.handleUsageExport)
	group.POST("/import", s.handleUsageImport)
	group.GET("/status", s.handleStatus)
	group.GET("/dead-letters", s.handleDeadLetters)
	group.GET("/dead-letters/export", s.handleDeadLettersExport)
	group.GET("/quota-cache", s.handleQuotaCacheGet)
	group.PUT("/quota-cache", s.handleQuotaCachePut)
	group.DELETE("/quota-cache", s.handleQuotaCacheDelete)
	group.GET("/model-prices", s.handleModelPricesGet)
	group.PUT("/model-prices", s.handleModelPricesPut)
	group.POST("/model-prices/sync", s.handleModelPricesSync)
}

func (s *Server) handleUsage(c *gin.Context) {
	events, err := s.store.RecentEvents(c.Request.Context(), s.cfg.QueryLimit)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}
	c.JSON(http.StatusOK, internalusage.BuildPayload(events))
}

func (s *Server) handleUsageExport(c *gin.Context) {
	data, err := s.store.ExportJSONL(c.Request.Context())
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}
	if accountInspectionScheduleExporter != nil {
		schedule, ok, err := accountInspectionScheduleExporter()
		if err != nil {
			c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
			return
		}
		if ok {
			line, err := json.Marshal(accountInspectionScheduleExportRecord{
				RecordType: accountInspectionScheduleExportRecordType,
				Version:    1,
				Schedule:   schedule,
				ExportedAt: time.Now().UnixMilli(),
			})
			if err != nil {
				c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
				return
			}
			data = append(data, line...)
			data = append(data, '\n')
		}
	}
	c.Header("Content-Type", "application/x-ndjson")
	c.Header("Content-Disposition", `attachment; filename="usage-events.jsonl"`)
	_, _ = c.Writer.Write(data)
}

func (s *Server) handleUsageImport(c *gin.Context) {
	reader := bufio.NewScanner(c.Request.Body)
	reader.Buffer(make([]byte, 64*1024), 10*1024*1024)
	events := make([]internalusage.Event, 0)
	var modelPrices map[string]ModelPrice
	modelPriceRecords := 0
	var accountInspectionSchedule json.RawMessage
	accountInspectionScheduleRecords := 0
	failed := 0
	for reader.Scan() {
		line := strings.TrimSpace(reader.Text())
		if line == "" {
			continue
		}
		if schedule, ok, err := parseAccountInspectionScheduleImportRecord([]byte(line)); err != nil {
			failed++
			continue
		} else if ok {
			accountInspectionSchedule = schedule
			accountInspectionScheduleRecords++
			continue
		}
		if prices, ok, err := parseModelPricesImportRecord([]byte(line)); err != nil {
			failed++
			continue
		} else if ok {
			modelPrices = prices
			modelPriceRecords++
			continue
		}
		event, err := internalusage.NormalizeRaw([]byte(line))
		if err != nil {
			failed++
			continue
		}
		events = append(events, event)
	}
	if err := reader.Err(); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}
	result, err := s.store.InsertEvents(c.Request.Context(), events)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}
	if modelPrices != nil {
		if err := s.store.SetModelPrices(c.Request.Context(), modelPrices); err != nil {
			c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
			return
		}
	}
	if accountInspectionSchedule != nil && accountInspectionScheduleImporter != nil {
		if err := accountInspectionScheduleImporter(accountInspectionSchedule); err != nil {
			c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
			return
		}
	}
	c.JSON(http.StatusOK, gin.H{
		"added":                            result.Inserted,
		"skipped":                          result.Skipped,
		"total":                            len(events),
		"failed":                           failed,
		"modelPrices":                      len(modelPrices),
		"modelPriceRecords":                modelPriceRecords,
		"accountInspectionSchedule":        accountInspectionSchedule != nil,
		"accountInspectionScheduleRecords": accountInspectionScheduleRecords,
	})
}

func parseAccountInspectionScheduleImportRecord(raw []byte) (json.RawMessage, bool, error) {
	var header struct {
		RecordType string `json:"record_type"`
	}
	if err := json.Unmarshal(raw, &header); err != nil {
		return nil, false, err
	}
	if header.RecordType != accountInspectionScheduleExportRecordType {
		return nil, false, nil
	}

	var record accountInspectionScheduleExportRecord
	if err := json.Unmarshal(raw, &record); err != nil {
		return nil, true, err
	}
	if len(record.Schedule) == 0 {
		return nil, true, nil
	}
	return record.Schedule, true, nil
}

func parseModelPricesImportRecord(raw []byte) (map[string]ModelPrice, bool, error) {
	var header struct {
		RecordType string `json:"record_type"`
	}
	if err := json.Unmarshal(raw, &header); err != nil {
		return nil, false, err
	}
	if header.RecordType != modelPricesExportRecordType {
		return nil, false, nil
	}

	var record modelPricesExportRecord
	if err := json.Unmarshal(raw, &record); err != nil {
		return nil, true, err
	}
	if record.Prices == nil {
		record.Prices = map[string]ModelPrice{}
	}
	return record.Prices, true, nil
}

func (s *Server) handleStatus(c *gin.Context) {
	events, deadLetters, err := s.store.Counts(c.Request.Context())
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}
	stats := ServiceStats{}
	if s.statsProvider != nil {
		stats = s.statsProvider.Stats()
	}
	c.JSON(http.StatusOK, gin.H{
		"service":     "embedded-usage-service",
		"dbPath":      s.cfg.DBPath,
		"events":      events,
		"deadLetters": deadLetters,
		"runtime":     stats,
	})
}

func (s *Server) handleDeadLetters(c *gin.Context) {
	limit := parseQueryInt(c, "limit", 50)
	offset := parseQueryInt(c, "offset", 0)
	page, err := s.store.DeadLetters(c.Request.Context(), limit, offset)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}
	c.JSON(http.StatusOK, page)
}

func (s *Server) handleDeadLettersExport(c *gin.Context) {
	c.Header("Content-Type", "application/x-ndjson")
	c.Header("Content-Disposition", `attachment; filename="usage-dead-letters.jsonl"`)
	if err := s.store.WriteDeadLettersJSONL(c.Request.Context(), c.Writer); err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
	}
}

func (s *Server) handleQuotaCacheGet(c *gin.Context) {
	if c.Query("stats") == "1" || c.Query("stats") == "true" {
		stats, err := s.store.QuotaCacheStats(c.Request.Context())
		if err != nil {
			c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
			return
		}
		c.JSON(http.StatusOK, stats)
		return
	}

	provider := strings.TrimSpace(c.Query("provider"))
	fileName := strings.TrimSpace(c.Query("fileName"))
	entries, err := s.store.GetQuotaCache(c.Request.Context(), provider, fileName)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}
	c.JSON(http.StatusOK, gin.H{"items": entries})
}

func (s *Server) handleQuotaCachePut(c *gin.Context) {
	var entry QuotaCacheEntry
	if err := json.NewDecoder(c.Request.Body).Decode(&entry); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}
	entry.Provider = strings.TrimSpace(entry.Provider)
	entry.FileName = strings.TrimSpace(entry.FileName)
	if entry.Provider == "" || entry.FileName == "" || len(entry.Data) == 0 {
		c.JSON(http.StatusBadRequest, gin.H{"error": "provider, fileName and data are required"})
		return
	}
	if err := s.store.SetQuotaCache(c.Request.Context(), entry); err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}
	c.JSON(http.StatusOK, gin.H{"ok": true})
}

func (s *Server) handleQuotaCacheDelete(c *gin.Context) {
	provider := strings.TrimSpace(c.Query("provider"))
	fileName := strings.TrimSpace(c.Query("fileName"))
	if err := s.store.DeleteQuotaCache(c.Request.Context(), provider, fileName); err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}
	c.JSON(http.StatusOK, gin.H{"ok": true})
}

func (s *Server) handleModelPricesGet(c *gin.Context) {
	prices, err := s.store.GetModelPrices(c.Request.Context())
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}
	c.JSON(http.StatusOK, gin.H{"prices": prices})
}

func (s *Server) handleModelPricesPut(c *gin.Context) {
	var payload struct {
		Prices map[string]ModelPrice `json:"prices"`
	}
	if err := json.NewDecoder(c.Request.Body).Decode(&payload); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}
	if payload.Prices == nil {
		payload.Prices = map[string]ModelPrice{}
	}
	if err := s.store.SetModelPrices(c.Request.Context(), payload.Prices); err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}
	c.JSON(http.StatusOK, gin.H{"ok": true})
}

func (s *Server) handleModelPricesSync(c *gin.Context) {
	prices, err := fetchLiteLLMModelPrices(c.Request.Context())
	if err != nil {
		c.JSON(http.StatusBadGateway, gin.H{"error": err.Error()})
		return
	}
	syncedAt := time.Now().UnixMilli()
	if err := s.store.UpsertModelPrices(c.Request.Context(), prices, syncedAt); err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}
	c.JSON(http.StatusOK, gin.H{"ok": true, "synced": len(prices), "syncedAtMs": syncedAt})
}

type liteLLMModelPriceRecord map[string]any

func fetchLiteLLMModelPrices(ctx context.Context) (map[string]ModelPrice, error) {
	req, err := http.NewRequestWithContext(ctx, http.MethodGet, liteLLMModelPricesURL, nil)
	if err != nil {
		return nil, err
	}
	client := &http.Client{Timeout: 20 * time.Second}
	resp, err := client.Do(req)
	if err != nil {
		return nil, err
	}
	defer resp.Body.Close()
	if resp.StatusCode < 200 || resp.StatusCode >= 300 {
		return nil, fmt.Errorf("litellm model prices returned status %d", resp.StatusCode)
	}
	body, err := io.ReadAll(io.LimitReader(resp.Body, 20*1024*1024))
	if err != nil {
		return nil, err
	}
	var payload map[string]liteLLMModelPriceRecord
	if err := json.Unmarshal(body, &payload); err != nil {
		return nil, err
	}

	prices := make(map[string]ModelPrice)
	for model, record := range payload {
		price, ok := modelPriceFromLiteLLMRecord(model, record)
		if ok {
			prices[model] = price
		}
	}
	return prices, nil
}

func modelPriceFromLiteLLMRecord(model string, record liteLLMModelPriceRecord) (ModelPrice, bool) {
	prompt := numberFromRecord(record, "input_cost_per_token") * 1_000_000
	completion := numberFromRecord(record, "output_cost_per_token") * 1_000_000
	cache := numberFromRecord(record, "cache_read_input_token_cost") * 1_000_000
	if cache == 0 {
		cache = numberFromRecord(record, "cache_creation_input_token_cost") * 1_000_000
	}
	if cache == 0 {
		cache = prompt
	}
	if prompt == 0 && completion == 0 && cache == 0 {
		return ModelPrice{}, false
	}
	raw, _ := json.Marshal(record)
	return ModelPrice{
		Prompt:        prompt,
		Completion:    completion,
		Cache:         cache,
		Source:        "litellm",
		SourceModelID: model,
		RawJSON:       raw,
	}, true
}

func numberFromRecord(record liteLLMModelPriceRecord, key string) float64 {
	value, ok := record[key]
	if !ok || value == nil {
		return 0
	}
	switch typed := value.(type) {
	case float64:
		return typed
	case string:
		parsed, err := strconv.ParseFloat(strings.TrimSpace(typed), 64)
		if err == nil {
			return parsed
		}
	}
	return 0
}

func parseQueryInt(c *gin.Context, key string, fallback int) int {
	value := strings.TrimSpace(c.Query(key))
	if value == "" {
		return fallback
	}
	parsed, err := strconv.Atoi(value)
	if err != nil {
		return fallback
	}
	return parsed
}
