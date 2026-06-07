# Research Search Agent

Based on `ETH-NEXUS/nexus-fullstack-example`, this project now uses SearxNG for discovery and Crawl4AI for page parsing, with Django REST Framework, PostgreSQL, Redis, Celery, Vue 3, and Nuxt 4 around it.

It is designed to:

- authenticate app requests with Cloudflare Access identity claims
- track multiple topics, each with independent search criteria
- let you run live ad hoc SearxNG searches before saving them as tracked topics
- search configurable public, research, and custom source scopes via SearxNG
- enrich discovered pages with Crawl4AI markdown extraction
- store results in PostgreSQL and keep them searchable
- scope saved topics, source scopes, runs, and stored results to the signed-in user
- highlight what is still new
- present everything in a black / green / white hacker-style UI that works on desktop and iPhone-sized screens

## What Ships

The seeded app comes with:

- a `Research Data Exchange Landscape` topic using:
  - `"data platform"`
  - `"research data exchange"`
  - `"research data exchange format"`
- a `Public Web` SearxNG scope
- a `Research Repositories` SearxNG scope
- per-topic interval scheduling, defaulting to `Every 1 day`

## Stack

Backend:

- Django 5
- Django REST Framework
- Celery + django-celery-beat + django-celery-results
- PostgreSQL
- Redis
- `httpx` for SearxNG requests
- `crawl4ai` for markdown extraction

Frontend:

- Nuxt 4
- Vue 3
- Tailwind CSS 4

Services:

- local SearxNG container
- Crawl4AI running inside the API / worker image
- optional Envoy edge proxy through the `proxy` compose profile
- optional Cloudflare Tunnel connector through the `tunnel` compose profile

## Quick Start

```bash
docker compose up -d --build
```

Services:

- Envoy HTTP: `http://localhost`
- Frontend: `http://localhost:8077`
- API: `http://localhost:5077/api/v1/`
- Admin: `http://localhost:8077/admin`
- Swagger: `http://localhost:8077/api/v1/schema/swagger-ui/`
- SearxNG: `http://localhost:8888`

Default admin credentials:

- username: `admin`
- password: `admin`

If you want a clean env file for another machine:

```bash
cp .env.TEMPLATE .env
```

Key environment variables:

- `SEARXNG_BASE_URL`
- `SEARXNG_TIMEOUT_S`
- `CRAWL4AI_MAX_PAGES_PER_RUN`
- `CLOUDFLARE_ACCESS_TEAM_DOMAIN`
- `CLOUDFLARE_ACCESS_AUDIENCE`
- `ENVOY_HTTP_HOST_PORT`
- `TUNNEL_TOKEN`

## Envoy Proxy

The optional `envoy` service listens for local HTTP traffic and routes `/api`, `/admin`, `/static`, and `/media` to Django while routing all other paths to Nuxt.

## Cloudflare Tunnel

The optional `cloudflare-tunnel` service runs `cloudflare/cloudflared` as a connector for a remotely-managed Cloudflare Tunnel.
Set `TUNNEL_TOKEN` in `.env` and include `tunnel` in `COMPOSE_PROFILES` to run it with the rest of the dev stack.

## Authentication

The UI and API now expect Cloudflare Access to sit in front of the app.
After Access validates the browser, Django verifies the `Cf-Access-Jwt-Assertion` token, provisions or refreshes a matching user record, and scopes saved searches to that Cloudflare identity.

Set these environment variables to match your Zero Trust application:

- `CLOUDFLARE_ACCESS_TEAM_DOMAIN`
- `CLOUDFLARE_ACCESS_AUDIENCE`

The Django admin remains available with the local admin account if you need direct admin access.

## Key API Endpoints

- `GET /api/v1/auth/user/`
- `GET /api/v1/dashboard/`
- `POST /api/v1/searxng/search/`
- `GET/POST /api/v1/topics/`
- `PATCH/DELETE /api/v1/topics/<slug>/`
- `POST /api/v1/topics/<slug>/run_now/`
- `POST /api/v1/topics/<slug>/acknowledge/`
- `GET/POST /api/v1/source-scopes/`
- `PATCH/DELETE /api/v1/source-scopes/<id>/`
- `GET /api/v1/results/`
- `POST /api/v1/results/acknowledge/`
- `GET /api/v1/runs/`
- `GET/PATCH /api/v1/provider-config/<id>/`

## Live Search

The web UI now starts with a live Search workspace:

- run an immediate SearxNG query with a basic search bar
- open an advanced panel for categories, engines, language, time range, domain filters, and raw passthrough params
- save the current search as a new topic, optionally creating a dedicated source scope from the live filters

## Topic Configuration Model

Each topic supports:

- a name and description
- multiple search queries
- required terms
- excluded terms
- lookback window in days
- max results per query
- attached source scopes
- enabled / disabled state

Each source scope supports:

- `public`, `research`, or `custom` kind
- freeform SearxNG categories
- optional SearxNG engine filters
- language
- safe-search level
- time range mode
- max results
- include / exclude domain lists

## Scheduling

Celery beat runs `core.tasks.dispatch_due_topic_searches` every minute.

Each topic now carries its own interval schedule:

- every `x` minutes
- every `x` hours
- every `x` days
- every `x` weeks

Manual options:

```bash
docker compose exec api python manage.py db init
docker compose exec api python manage.py shell
```

Or trigger a topic directly from the web UI using `Run now`.

## Notes

- The previous external search-provider wiring has been removed in favor of SearxNG + Crawl4AI.
- SearxNG is configured locally through [ops/searxng/settings.yml](/Users/davmeyer/git/search-agent/ops/searxng/settings.yml:1).
- Crawl4AI browser dependencies are installed as part of the API image build.
