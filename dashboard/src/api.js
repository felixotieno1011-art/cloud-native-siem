const BACKEND = "http://127.0.0.1:8080";

async function getJson(path) {
  const res = await fetch(`${BACKEND}${path}`);
  if (!res.ok) {
    throw new Error(`${path} -> ${res.status}`);
  }
  return res.json();
}

export async function fetchEvents(limit = 20) {
  const data = await getJson(`/api/events?limit=${limit}`);
  return data.events || [];
}

export async function fetchAlerts(limit = 20) {
  const data = await getJson(`/api/alerts?limit=${limit}`);
  return data.alerts || [];
}

export async function fetchHealth() {
  return getJson("/health");
}


export async function ackAlert(id) {
  const res = await fetch(`${BACKEND}/api/alerts/${id}/ack`, {
    method: "POST",
  });
  if (!res.ok) {
    throw new Error(`ack ${id} -> ${res.status}`);
  }
  return res.json();
}

export function connectLiveFeed(onEvent, onAlert) {
  const ws = new WebSocket("ws://127.0.0.1:8080/ws/live");
  ws.onmessage = (msg) => {
    const parsed = JSON.parse(msg.data);
    if (parsed.queue.includes("events")) onEvent(parsed.data);
    if (parsed.queue.includes("alerts")) onAlert(parsed.data);
  };
  return ws;
}
