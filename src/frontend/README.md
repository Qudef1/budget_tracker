# Saldo frontend

React + TypeScript + Vite. The initial stage provides a route skeleton and a local
API proxy, registration, sign-in, route guards, transaction and category CRUD, monthly
limits, savings goals, financial analytics and administration. Styles are provisional and
Figma styling is not implemented yet.
The short-lived access token is held in React memory and is discarded on page reload.

## Local development

Start the FastAPI backend on `127.0.0.1:8000`, then in this directory run:

```powershell
npm.cmd install
npm.cmd run dev
```

Requests to `/api/...` are forwarded to the backend with `/api` removed. To use a
different backend, set `VITE_PROXY_TARGET` in the shell before starting Vite.
This proxy is for development; production hosting needs its own reverse proxy.

Use `npm.cmd run build` for TypeScript checking and the production bundle,
`npm.cmd run lint` for linting, and `npm.cmd run test` for authentication tests.
`npm.cmd` avoids PowerShell's script policy issue.

## Implementation plan

1. Routing, shared components and design tokens (visual design pending Figma access).
2. In-memory OAuth2 access token, `/auth/me`, role guards and application layout (implemented).
3. Transaction and category CRUD (implemented).
4. Monthly limits, execution/history and savings goals (implemented).
5. Monthly, comparative and category analytics (implemented).
6. Admin user management and aggregate statistics (implemented).
7. End-to-end checks, accessibility and responsive polish.

Existing API endpoints are the contract; route placeholders do not contain mock data.
Archived limits are not listed by the backend, so retain the displayed limit ID to find
its history after a reload. The backend does not include currency in archived history.
Adding to a savings goal reads the current amount and then updates it; this operation is not
atomic across tabs or devices because the backend only supports setting the absolute amount.
