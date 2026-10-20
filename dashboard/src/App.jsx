import { useEffect, useState } from "react";
import { ackAlert, fetchAlerts, fetchEvents, fetchHealth, connectLiveFeed } from "./api";
import "./App.css";

const POLL_MS = 3000;

function formatTime(iso) {
  if (!iso) return "—";
  try {
    return new Date(iso).toLocaleTimeString();
  } catch {
    return iso;
  }
}

function AlertRow({ alert, onAck }) {
  const acked = Boolean(alert.acknowledged_at);
  return (
    <li className={`alert alert-${alert.severity}${acked ? " acked" : ""}`}>
      <span className="badge">{alert.severity}</span>
      <span className="alert-title">{alert.title}</span>
      <span className="alert-meta">
        {alert.rule_id} · {alert.agent_id} · {formatTime(alert.created_at)}
        {acked && <> · ✓ acked {formatTime(alert.acknowledged_at)}</>}
      </span>
      {!acked && (
        <button className="ack-btn" onClick={() => onAck(alert.id)}>
          Acknowledge
        </button>
      )}
    </li>
  );
}

function EventRow({ event }) {
  const { type, ...rest } = event.payload || {};
  const payloadStr = JSON.stringify(rest).slice(0, 80);
  return (
    <tr>
      <td>{event.event_type}</td>
      <td>{event.agent_id}</td>
      <td className="mono">{payloadStr}</td>
      <td>{formatTime(event.received_at)}</td>
    </tr>
  );
}


export default function App() {
  const [health, setHealth] = useState(null);
  const [alerts, setAlerts] = useState([]);
  const [events, setEvents] = useState([]);
  const [error, setError] = useState(null);
  const [filter, setFilter] = useState("all");

  async function handleAck(id) {
    try {
      await ackAlert(id);
      const [a, e] = await Promise.all([fetchAlerts(20), fetchEvents(20)]);
      setAlerts(a);
      setEvents(e);
    } catch (err) {
      setError(err.message);
    }
  }

  useEffect(() => {
    // 1. Initial fetch & health retry
    let stop = false;
    async function checkHealth() {
      if (stop) return;
      try {
        const h = await fetchHealth();
        setHealth(h);
        setError(null);
        // If we got health, do the initial data load
        const [a, e] = await Promise.all([fetchAlerts(20), fetchEvents(20)]);
        if (!stop) { setAlerts(a); setEvents(e); }
      } catch (err) {
        if (!stop) {
          setHealth(null);
          setError(err.message);
          setTimeout(checkHealth, 5000); // retry in 5s
        }
      }
    }
    checkHealth();

    // 2. Live WebSocket feed
    const ws = connectLiveFeed(
      (newEvent) => {
        // Normalize the Redis payload to match Postgres format
        const formatted = {
          id: "live-" + Date.now(),
          event_type: newEvent.type || "unknown",
          agent_id: newEvent._agent_id || "unknown",
          payload: newEvent,
          received_at: new Date(newEvent.timestamp * 1000).toISOString(),
        };
        setEvents((prev) => [formatted, ...prev].slice(0, 20));
      },
      (newAlert) => {
        const formatted = {
          id: "live-" + Date.now(),
          rule_id: newAlert.rule_id,
          severity: newAlert.severity,
          title: newAlert.title,
          agent_id: newAlert._agent_id || "unknown",
          details: newAlert.details,
          created_at: new Date().toISOString(),
          acknowledged_at: null,
        };
        setAlerts((prev) => [formatted, ...prev].slice(0, 20));
      }
    );
    
    ws.onopen = () => setError(null);
    ws.onerror = () => setError("Live feed disconnected");
    return () => { stop = true; ws.close(); };
  }, []);

  const filteredAlerts = alerts.filter(
    (a) => filter === "all" || a.severity === filter
  );

  return (
    <div className="app">
      <header>
        <h1>Cloud-Native SIEM</h1>
        <div className="status">
          {error ? (
            <span className="err">backend unreachable: {error}</span>
          ) : health ? (
            <span className="ok">backend ok · v{health.version}</span>
          ) : (
            <span>connecting…</span>
          )}
        </div>
      </header>

      <main>
        <section className="panel">
          <h2>
            Alerts <span className="count">{filteredAlerts.length}</span>
            <select
              value={filter}
              onChange={(e) => setFilter(e.target.value)}
              className="filter-select"
            >
              <option value="all">All</option>
              <option value="high">High</option>
              <option value="medium">Medium</option>
              <option value="low">Low</option>
            </select>
          </h2>
          {filteredAlerts.length === 0 ? (
            <p className="empty">No alerts match this filter.</p>
          ) : (
            <ul className="alerts">
              {filteredAlerts.map((a) => (
                <AlertRow key={a.id} alert={a} onAck={handleAck} />
              ))}
            </ul>
          )}
        </section>

        <section className="panel">
          <h2>Events <span className="count">{events.length}</span></h2>
          <table className="events">
            <thead>
              <tr>
                <th>Type</th>
                <th>Agent</th>
                <th>Payload</th>
                <th>Time</th>
              </tr>
            </thead>
            <tbody>
              {events.map((e) => <EventRow key={e.id} event={e} />)}
            </tbody>
          </table>
        </section>
      </main>
    </div>
  );
}
