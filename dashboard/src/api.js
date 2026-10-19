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
