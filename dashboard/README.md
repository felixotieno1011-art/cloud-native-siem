# Cloud-Native SIEM — Dashboard

React + Vite frontend for the Cloud-Native SIEM backend.

## Run

From this directory:

    npm install
    npm run dev -- --host 127.0.0.1 --port 5173

Then open http://127.0.0.1:5173/ in a browser.

The dashboard expects the backend at `http://127.0.0.1:8080`.
Start it with `../dev.sh` from the repo root.

## Views

- **Alerts** — recent detections from `GET /api/alerts`
- **Events** — recent raw events from `GET /api/events`

Polls every 3 seconds. Vite HMR handles hot reload during development.
