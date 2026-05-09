package embeddedusage

import (
	"context"
	"sync"
	"time"

	"github.com/router-for-me/CLIProxyAPI/v6/internal/embeddedusage/internalusage"
	"github.com/router-for-me/CLIProxyAPI/v6/internal/redisqueue"
	log "github.com/sirupsen/logrus"
)

type Service struct {
	cfg    Config
	store  *Store
	server *Server
	mu     sync.Mutex
	stats  ServiceStats
}

type ServiceStats struct {
	LastConsumedAtMS int64  `json:"lastConsumedAtMs"`
	LastInsertedAtMS int64  `json:"lastInsertedAtMs"`
	TotalInserted    int64  `json:"totalInserted"`
	TotalSkipped     int64  `json:"totalSkipped"`
	LastError        string `json:"lastError,omitempty"`
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

	service := &Service{
		cfg:   cfg,
		store: store,
	}
	service.server = NewServer(cfg, store, service)
	go service.collect(ctx)
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

func (s *Service) Stats() ServiceStats {
	if s == nil {
		return ServiceStats{}
	}
	s.mu.Lock()
	defer s.mu.Unlock()
	return s.stats
}

func (s *Service) recordConsumed(count int) {
	if count <= 0 {
		return
	}
	s.mu.Lock()
	s.stats.LastConsumedAtMS = time.Now().UnixMilli()
	s.mu.Unlock()
}

func (s *Service) recordInsertResult(result InsertResult) {
	s.mu.Lock()
	now := time.Now().UnixMilli()
	if result.Inserted > 0 {
		s.stats.LastInsertedAtMS = now
	}
	s.stats.TotalInserted += int64(result.Inserted)
	s.stats.TotalSkipped += int64(result.Skipped)
	s.stats.LastError = ""
	s.mu.Unlock()
}

func (s *Service) recordError(err error) {
	if err == nil {
		return
	}
	s.mu.Lock()
	s.stats.LastError = err.Error()
	s.mu.Unlock()
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

		s.recordConsumed(len(items))
		events := make([]internalusage.Event, 0, len(items))
		for _, item := range items {
			event, err := internalusage.NormalizeRaw(item)
			if err != nil {
				s.recordError(err)
				if addErr := s.store.AddDeadLetter(ctx, string(item), err); addErr != nil {
					s.recordError(addErr)
					log.WithError(addErr).Warn("failed to add embedded usage dead letter")
				}
				continue
			}
			events = append(events, event)
		}
		result, err := s.store.InsertEvents(ctx, events)
		if err != nil {
			s.recordError(err)
			log.WithError(err).Warn("failed to insert embedded usage events")
			continue
		}
		s.recordInsertResult(result)
	}
}
