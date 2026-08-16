# Frontend

React + TypeScript + Vite frontend for the Minervini NSE Scanner.

## Development

From this directory:

```bash
npm install
npm run dev
```

The Vite dev server runs on:

```text
http://127.0.0.1:5173
```

It proxies `/api` to the FastAPI backend on port 8000.

Start the backend from the repository root:

```bash
uv run minervini api
```

Then start the frontend:

```bash
cd frontend
npm install
npm run dev
```

## Production build

```bash
npm run build
```

The resulting `dist/` directory can be deployed to a static hosting service or served behind a reverse proxy.
