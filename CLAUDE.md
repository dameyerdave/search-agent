## Context

This is a full-stack web application that is currently in the progress of being developed.
It is currently running in docker containers on the hosts computer.
You do not need to write any tests. However you can test your code by interacting with the running containers.
Do not keep any deprecated or legacy code, if you decide to remove code, make sure to update all usages.

## Stack

- **Backend**: Django 5.2 + DRF 3.16, PostgreSQL, Redis, Celery
- **Frontend**: Nuxt 4 SPA, Vue 3, TypeScript, Pinia, TanStack Query, Tailwind, @nuxt/ui

## File Locations

**Backend** (`api/app/core/`): models.py, serializers.py, viewsets.py, permissions.py, tasks.py

**Frontend** (`ui/app/app/`): components/, stores/, plugins/, locales/

 ## Guardrails (Important)

- Do not introduce new architectural patterns, libraries, or frameworks without asking the user for confirmation.
- If we do introduce a new pattern, framework or helper/abstraction, document its usage in the CLAUDE.md file with a short description and example.
- Before editing any file, always check its current size (roughly: line count). Keep it under ~400 lines. If your change would push it beyond that, refactor it into multiple files.
- If you are unsure about a library/framework detail, check the official docs on the internet (Django, DRF, Nuxt, Vue, Pinia, Tailwind, etc.).
- Do not create new top-level folders without checking existing structure.
- Do not duplicate existing abstractions or helpers (e.g. HTTP clients, stores, auth logic).
- Prefer extending existing modules over creating parallel ones.

## Project-Specific Patterns

**Permissions** - define constants in `permissions.py`:
```python
class Groups:
    EDITOR = "editor"

class Perms:
    VIEW_BOOK = "core.view_book"
```

**Object-level permissions** - use django-guardian:
```python
from guardian.shortcuts import assign_perm, get_objects_for_user
```

**API calls** - use Orval-generated functions (not raw fetch/axios):
```typescript
// In components: use generated Vue Query composables
import { useBooksList } from '~/app/api/generated/books/books'
const { data, isFetching, refetch } = useBooksList()

// In stores: use generated raw functions for imperative calls
import { authLoginCreate } from '~/app/api/generated/auth/auth'
await authLoginCreate({ username, password })
```

**Regenerate API layer** after OpenAPI schema changes:
```bash
pnpm generate:api
```

**Pinia stores** - composition API style with `defineStore(() => {})`

**Dashboard stores** - the `app.vue` SPA shell is split into 5 composition stores under
`ui/app/app/stores/`, each owning state/actions for one workspace (or shared dashboard
state). Leaf workspace stores may call `useDashboardStore()` at top-level setup for shared
computed (e.g. `topics`); `dashboard.ts` calls into leaf stores from inside action bodies
only (never at top-level setup) to avoid init-order cycles:
```typescript
// dashboard.ts action reaching into a leaf store
const editTopicInConfigure = (topic: SearchTopic) => {
  activeWorkspace.value = 'configure'
  useConfigureWorkspaceStore().openTopicEditor(topic)
}
```
- `stores/dashboard.ts` - shared dashboard payload (`topics`/`sources`/`provider`/`stats`),
  `activeWorkspace`, `busyLabel`/`errorMessage`, `bootstrap()` (called from `app.vue`'s
  `onMounted`), provider form, and cross-workspace topic actions
- `stores/searchWorkspace.ts`, `stores/exploreWorkspace.ts`, `stores/configureWorkspace.ts`,
  `stores/runsWorkspace.ts` - per-workspace form state/filters and actions
- `app/utils/dashboard.ts` - pure formatting/derivation helpers (`formatDate`,
  `summarizeStatus`, `describeCategories`, etc.) with **no i18n inside** - components
  translate the returned discriminators via local helpers, e.g.
  `t(\`dashboard.common.status.${summarizeStatus(status)}\`)`

**UI** - use @nuxt/ui components: `UButton`, `UCard`, `UBadge`, `UInput`, etc.

**i18n** - use `const { t } = useI18n()` for all user-facing strings

**PWA install support** - keep install metadata in static files and mount the installer once in the root shell:
```typescript
// app shell
<PwaInstallButton />
```

- Manifest: `ui/app/public/manifest.webmanifest`
- Service worker: `ui/app/public/sw.js`
- Install UI: `ui/app/app/components/PwaInstallButton.vue`

**OpenStreetMap overlay** - keep map fetching and tile rendering in focused components. The map is mounted inside the Explore workspace and follows the selected topic/result filters:
```typescript
<SearchMapWorkspace
  :topic-slug="resultFilters.topic"
  :topic-name="selectedTopic?.name ?? ''"
/>
```

- Map workspace: `ui/app/app/components/SearchMapWorkspace.vue`
- Tile map: `ui/app/app/components/SearchResultsMap.vue`
- Aggregated API: `GET /api/v1/results/map/`
- Backfill command: `python manage.py backfill_result_locations`

## Auth

Session-based with CSRF (auto-handled by `app/api/mutator/custom-fetch.ts`).
Endpoints: `/api/v1/auth/login/`, `/api/v1/auth/logout/`, `/api/v1/auth/user/`

**Dev auto-login** - when `DJANGO_DEBUG=True` and `DEV_AUTO_LOGIN_EMAIL` is set (default
`test@test.com` in `.env`/`.env.TEMPLATE`), every API request is authenticated as that
user via `core.authentication.DevAutoLoginAuthentication` (prepended to
`DEFAULT_AUTHENTICATION_CLASSES`). The user is created on first use as a superuser in the
`editor` group. This lets local dev run without Cloudflare Access/Tunnel in front of the
app - set `DEV_AUTO_LOGIN_EMAIL=` (empty) to require real Cloudflare Access tokens again.

## Orval (API Code Generation)

Orval generates typed Vue Query composables and raw fetch functions from the OpenAPI schema.

- **Config**: `ui/app/orval.config.ts`
- **Generated output**: `ui/app/app/api/generated/` (gitignored, regenerate with `pnpm generate:api`)
- **Custom fetch mutator**: `ui/app/app/api/mutator/custom-fetch.ts` — handles CSRF tokens and `credentials: 'include'`
- **OpenAPI schema**: `ui/app/openapi/api/openapi.json` (auto-updated by `watch-openapi.mjs`)

## Kubernetes Deployment (Helm)

CI/CD builds `api`/`ui` images, pushes them to Docker Hub, and runs `helm upgrade --install` against the cluster.

- **Chart**: `kube/helm/search-agent/` — one Deployment/StatefulSet per docker-compose service (api, ui, celery-worker, celery-beat, postgres, redis, searxng, envoy, cloudflared)
- **Values**: `kube/helm/search-agent/values.yaml` — edit `config.*` (domains, allowed hosts) directly; `secrets.*` and image tags are supplied at deploy time, never committed
- **Workflow**: `.github/workflows/deploy.yml` — required repo secrets are documented in its header comment
- **Local kubeconfig**: `kube/kubeconfig.yaml` is gitignored — never commit cluster credentials; CI reads the cluster config from the `KUBE_CONFIG` secret (base64-encoded)
- Service hostnames inside the cluster match the docker-compose hostnames (`api`, `ui`, `postgres`, `redis`, `searxng`, `envoy`), so `ops/envoy/envoy.yaml` and `ops/searxng/settings.yml` are reused unmodified via `--set-file`
- External access is via Cloudflare Tunnel (`cloudflared`) routed to the in-cluster `envoy` service — update the tunnel's public hostname route in the Cloudflare Zero Trust dashboard to point at `http://envoy.search-agent.svc.cluster.local:80`
