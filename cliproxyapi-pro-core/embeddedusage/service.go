package embeddedusage

import (
	"bytes"
	"context"
	"fmt"
	"net/http"
	"strings"
	"time"

	"github.com/router-for-me/CLIProxyAPI/v6/internal/embeddedusage/internalusage"
	"github.com/router-for-me/CLIProxyAPI/v6/internal/redisqueue"
	log "github.com/sirupsen/logrus"
)

type Service struct {
	cfg    Config
	store  *Store
	server *Server
}

func Start(ctx context.Context) (*Service, error) {
	cfg := LoadConfig()
	if !cfg.Enabled {
		log.Info("embedded usage service disabled")
		return nil, nil
	}

	store, err := OpenStore(cfg.DBPath)
	if err != nil {
		return nil, err
	}

	redisqueue.SetEnabled(true)
	redisqueue.SetUsageStatisticsEnabled(true)

	service := &Service{
		cfg:   cfg,
		store: store,
	}
	service.server = NewServer(cfg, store)
	go service.collect(ctx)
	go service.maintain(ctx)
	go service.runWebDAVBackups(ctx)
	go func() {
		<-ctx.Done()
		if err := store.Close(); err != nil {
			log.WithError(err).Warn("failed to close embedded usage store")
		}
	}()

	log.Infof("embedded usage service started with db %s", cfg.DBPath)
	return service, nil
}

func (s *Service) Server() *Server {
	if s == nil {
		return nil
	}
	return s.server
}

func (s *Service) collect(ctx context.Context) {
	ticker := time.NewTicker(s.cfg.PollInterval)
	defer ticker.Stop()

	for {
		select {
		case <-ctx.Done():
			return
		default:
		}

		items := redisqueue.PopOldest(s.cfg.BatchSize)
		if len(items) == 0 {
			select {
			case <-ctx.Done():
				return
			case <-ticker.C:
				continue
			}
		}

		events := make([]internalusage.Event, 0, len(items))
		for _, item := range items {
			event, err := internalusage.NormalizeRaw(item)
			if err != nil {
				if addErr := s.store.AddDeadLetter(ctx, string(item), err); addErr != nil {
					log.WithError(addErr).Warn("failed to add embedded usage dead letter")
				}
				continue
			}
			events = append(events, event)
		}
		if _, err := s.store.InsertEvents(ctx, events); err != nil {
			log.WithError(err).Warn("failed to insert embedded usage events")
		}
	}
}

func (s *Service) maintain(ctx context.Context) {
	ticker := time.NewTicker(time.Hour)
	defer ticker.Stop()
	for {
		if deleted, err := s.store.ApplyRetention(ctx, time.Now()); err != nil {
			log.WithError(err).Warn("failed to apply embedded usage retention")
		} else if deleted > 0 {
			log.Infof("embedded usage retention deleted %d events", deleted)
		}
		select {
		case <-ctx.Done():
			return
		case <-ticker.C:
		}
	}
}

func (s *Service) runWebDAVBackups(ctx context.Context) {
	var lastBackup time.Time
	for {
		settings, err := s.store.GetMonitoringSettings(ctx)
		if err != nil {
			log.WithError(err).Warn("failed to load monitoring settings")
		} else if shouldRunWebDAVBackup(settings, lastBackup) {
			if err := s.backupToWebDAV(ctx, settings.WebDAV); err != nil {
				log.WithError(err).Warn("failed to backup embedded usage to WebDAV")
			} else {
				lastBackup = time.Now()
			}
		}

		select {
		case <-ctx.Done():
			return
		case <-time.After(time.Minute):
		}
	}
}

func shouldRunWebDAVBackup(settings MonitoringSettings, lastBackup time.Time) bool {
	webdav := normalizeMonitoringSettings(settings).WebDAV
	if !webdav.Enabled || webdav.URL == "" {
		return false
	}
	if lastBackup.IsZero() {
		return true
	}
	return time.Since(lastBackup) >= time.Duration(webdav.IntervalMinutes)*time.Minute
}

func (s *Service) backupToWebDAV(ctx context.Context, cfg MonitoringWebDAVBackupConfig) error {
	cfg = normalizeMonitoringSettings(MonitoringSettings{WebDAV: cfg}).WebDAV
	if !cfg.Enabled || cfg.URL == "" {
		return nil
	}
	data, err := s.server.exportJSONL(ctx)
	if err != nil {
		return err
	}
	url := strings.TrimRight(cfg.URL, "/") + fmt.Sprintf("/usage-export-%s.jsonl", time.Now().UTC().Format("20060102_150405"))
	req, err := http.NewRequestWithContext(ctx, http.MethodPut, url, bytes.NewReader(data))
	if err != nil {
		return err
	}
	req.Header.Set("Content-Type", "application/x-ndjson")
	if cfg.Username != "" || cfg.Password != "" {
		req.SetBasicAuth(cfg.Username, cfg.Password)
	}
	response, err := http.DefaultClient.Do(req)
	if err != nil {
		return err
	}
	defer response.Body.Close()
	if response.StatusCode < 200 || response.StatusCode >= 300 {
		return fmt.Errorf("webdav upload failed with status %d", response.StatusCode)
	}
	log.Infof("embedded usage backup uploaded to WebDAV: %s", url)
	return nil
}
