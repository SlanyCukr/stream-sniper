# Stream Sniper Frontend - Developer Instructions

React dashboard for Twitch stream/chat analytics: browse streams, replay a
Twitch-like chat, inspect chatter/message data, JWT auth, and an admin panel
(user management, system health, streamer tracking).

## Technology Stack

- **Framework**: Next.js 16 (App Router, Turbopack) + React 19
- **Language**: TypeScript throughout — every production file under
  `app|components|views|contexts|hooks|lib|utils` is `.ts/.tsx` under
  `strict: true` with `allowJs: false`. New code must be TypeScript; a stray
  `.js` import fails the typecheck.
- **UI**: Bootstrap 5.3 + `react-bootstrap`, `react-select`; SASS.
- **Data**: `@tanstack/react-query` (server-state cache), `axios` (single client
  in `lib/api/client.ts`; endpoint adapters in `lib/api/*.ts`).
- **Auth**: client-side JWT in `localStorage['token']`; `contexts/AuthContext.tsx`.
- **Output**: `output: 'standalone'` — a Node server runs in the prod container
  (replaces the old nginx container).

> There is no CRA, `react-scripts`, `react-router-dom`, `reactstrap`,
> `react-dotenv`, `apexcharts`, `react-window`, or `prop-types` anymore. Do not
> reintroduce them. Routing is file-based; env is server-side (see below).

## Setup & Commands

```bash
cd frontend
npm install            # regenerates package-lock.json (no --legacy-peer-deps needed)
npm run dev            # next dev --turbopack on :3000
npm run build          # next build -> .next/standalone/server.js (primary gate)
npm run start          # next start on :3000 (serves a production build)
npm run typecheck      # tsc --noEmit (strict, whole repo)
npm test -- --run      # Vitest suite
npx playwright install chromium # one-time local browser runtime setup
npm run test:e2e       # critical browser journeys; owns localhost:4173
npm run lint           # eslint . (advisory; build does not fail on lint)
npm run lint:fix
```

Bare-metal dev reads `.env.local` (gitignored) for `API_PROXY_TARGET`
(default `http://localhost:5002`). Start the FastAPI backend on 5002 for live data.
Playwright tests intercept `/api/**` at the browser boundary, so their deterministic
auth, stream-replay, and admin-session journeys do not require a live backend.

## API proxying (important)

The app always calls **relative `/api/...`** URLs. `next.config.ts` `rewrites()`
strips the `/api` prefix and forwards to the server-side env var
**`API_PROXY_TARGET`** (e.g. `/api/auth/me` -> `<target>/auth/me`). This mirrors
the old nginx `proxy_pass .../;` trailing-slash strip.

- Dev compose: `API_PROXY_TARGET=http://api:5002` (runtime — `next dev` re-reads it)
- Prod: **baked at build time** — `next build` writes rewrites into
  `routes-manifest.json`, so runtime env cannot change it. `Dockerfile.prod`
  sets `ARG/ENV API_PROXY_TARGET=http://stream-sniper-api:5002` before the
  build; override with `--build-arg` if the api service name ever changes.
- Bare metal: `API_PROXY_TARGET=http://localhost:5002` in `.env.local`

`lib/api/client.ts` owns the axios instance (`baseURL: '/api'`). A request interceptor
attaches `Authorization: Bearer <token>` from `localStorage` to **every** `/api`
call; a response interceptor clears the token and fires the registered
`onUnauthorized` handler (AuthContext's `logout`) on 401.

## Project Structure

No `src/` directory. Path alias `@/*` -> repo-relative (`./*`).

```
app/                       # App Router: file-based routes
  layout.tsx               # root <html data-bs-theme="dark">, global SCSS, Providers, LegacyHashRedirect
  providers.tsx            # QueryClientProvider + AuthProvider ('use client')
  error.tsx / global-error.tsx / not-found.tsx   # deliberately NO root loading.tsx (see Gotchas)
  login/page.tsx           # login (no app shell)
  (app)/                   # route group = FullLayout shell (sidebar + header)
    layout.tsx             # renders <FullLayout>
    page.tsx               # HOME = AllStreams
    stream/[id]/page.tsx   # params is a Promise -> use(params)
    chatter/page.tsx       # unified Chatter explorer (Footprint/Messages tabs); ?view= picks tab. Old /chatter-messages + /chatter-footprint 307-redirect here (next.config.ts redirects())
    profile/page.tsx
    admin/                 # admin/layout.tsx wraps children in <AdminGuard>
      page.tsx, dashboard/, users/(+create/), system/, tracking/(streamers/, jobs/)
components/                # client UI by capability (admin/, auth/, chatter/, community/, creator/, streams/, ...)
views/                     # route bodies grouped by owning product domain and imported by thin page.tsx wrappers
contexts/AuthContext.tsx
hooks/                     # capability folders mirror API/product domains (admin/, chatter/, community/, creator/, moments/, scene/, stream/)
lib/api/                   # client.ts plus domain endpoint adapters and exact wire DTOs
lib/auth/, lib/creator/, lib/stream/, lib/models/ # capability contracts and static UI models
utils/, styles/            # styles/style.scss is the SCSS entry
next.config.ts, tsconfig.json, eslint.config.mjs
Dockerfile (dev), Dockerfile.prod (multi-stage standalone, non-root)
```

### Routing conventions (App Router)

- A route = a `page.tsx`; the URL is its folder path. `(app)` is a route group
  (organizational, not in the URL). `[id]` is a dynamic segment.
- Client components need `'use client'` at the top. Every `components/**` and
  `views/**` file here is a client component.
- Route views follow their owning product domain: community lives in
  `views/community`, moments in `views/moments`, audience movement in
  `views/creator`, and scene-owned discovery surfaces in `views/scene`. Their
  `page.tsx` files stay thin and import one matching view. Reusable data/state and
  presentation remain in the matching `hooks/**` and `components/**` capability.
- Navigation: `useRouter()`/`usePathname()`/`useSearchParams()` from
  `next/navigation`; `<Link href>` from `next/link`. Dynamic `params` is a
  Promise — unwrap with `use(params)` in the page and pass values down as props.
- Legacy `/#/path` hash links are handled by `components/layout/LegacyHashRedirect.tsx`.

## Docker

```bash
docker-compose up frontend                       # dev: Dockerfile, :3000, bind-mount + polling HMR
docker-compose -f docker-compose.prod.yml up -d stream-sniper-frontend   # prod: Dockerfile.prod, host 3001 -> container 3000
```

Prod maps host `3001 -> 3000` (Node server, not nginx:80); the VPS reverse proxy
target port is unchanged. `Dockerfile.prod` runs `npm ci`, so a committed
`package-lock.json` must be in sync.

## Gotchas

- **Env is server-side.** No `REACT_APP_*` / `window.env` / `public/env.js`.
  Only `process.env.NODE_ENV` (statically inlined by Next) is used in code.
- **Add `'use client'`** to any new interactive component/view, else App Router
  treats it as a Server Component and hooks/`localStorage` break.
- **SCSS**: `next.config.ts` sets `sassOptions.includePaths: ['node_modules']`
  so bare `@import "bootstrap/scss/bootstrap"` resolves. Bootstrap emits Sass
  deprecation warnings (harmless). If Turbopack ever rejects `includePaths`,
  switch to `loadPaths`.
- **The codebase is fully TypeScript** (migrated 2026-07-19). `allowJs: false`
  is the regression guard: do not add `.js`/`.jsx` production files — the old
  checkJs boundary and unchecked-JS ratchet are gone because there is nothing
  left to ratchet.
- **ESLint** is flat-config (`eslint.config.mjs`) spreading
  `eslint-config-next`'s default array. Several React-19 rules
  (`react-hooks/set-state-in-effect`, `react-hooks/purity`,
  `react/no-unescaped-entities`) are downgraded to warnings so the lift-and-shift
  isn't blocked; `no-undef` is off for `.ts/.tsx` (TypeScript handles it).
- **Backend down is not a crash.** Pages must still render their shell +
  error/empty states; a failed `/api` proxy returns 500 but the page renders.
- **No root `app/loading.tsx` — on purpose.** A loading boundary above the
  dynamic routes makes Next commit HTTP 200 before `notFound()` in
  `stream/[id]`, `chatter/[id]`, and `creator/[id]/wrapped` can run, so invalid
  ids served the 404 UI with a 200 status (crawler-visible). Removing the
  boundary restores real 404s, and TTFB is unaffected (generateMetadata streams;
  views own their loading states via react-query). Don't reintroduce a
  `loading.tsx` at root or above these segments; `e2e/critical-journeys.spec.ts`
  guards the 404 status.
