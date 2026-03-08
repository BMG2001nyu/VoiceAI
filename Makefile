.PHONY: dev-up dev-down dev-logs dev-reset dev-status \
        backend frontend test-backend test-frontend lint

# ── Local services (Docker Compose) ──────────────────────────────────────────

dev-up:
	docker compose up -d
	@echo "Services starting…"
	@echo "  Redis    → localhost:6379"
	@echo "  Postgres → localhost:5432  (mc/mc @ missioncontrol)"
	@echo "  MinIO    → localhost:9000  (API) | localhost:9001 (console)"

dev-down:
	docker compose down

dev-logs:
	docker compose logs -f

## Wipe all volumes and restart fresh (destructive — loses all data)
dev-reset:
	docker compose down -v
	docker compose up -d

dev-status:
	docker compose ps

# ── Backend ───────────────────────────────────────────────────────────────────

backend:
	cd backend && source venv/bin/activate && \
	uvicorn main:app --reload --host 0.0.0.0 --port 8000

test-backend:
	cd backend && source venv/bin/activate && \
	pytest tests/ -x --tb=short -v

lint:
	cd backend && source venv/bin/activate && \
	ruff check . ../models/ ../agents/ && \
	black --check . ../models/ ../agents/

# ── Frontend ──────────────────────────────────────────────────────────────────

frontend:
	cd frontend && npm run dev

test-frontend:
	cd frontend && npm run test -- --run

# ── Postgres helpers ──────────────────────────────────────────────────────────

psql:
	docker compose exec postgres psql -U mc -d missioncontrol

redis-cli:
	docker compose exec redis redis-cli
