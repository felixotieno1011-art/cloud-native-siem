import { useEffect, useState } from "react";
import { ackAlert, fetchAlerts, fetchEvents, fetchHealth } from "./api";
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
    let stop = false;

    async function poll() {
      try {
        const [h, a, e] = await Promise.all([
          fetchHealth(),
          fetchAlerts(20),
          fetchEvents(20),
        ]);
        if (stop) return;
        setHealth(h);
        setAlerts(a);
        setEvents(e);
        setError(null);
      } catch (err) {
        if (!stop) setError(err.message);
      }
    }

    poll();
    const id = setInterval(poll, POLL_MS);
    return () => {
      stop = true;
      clearInterval(id);
    };
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
