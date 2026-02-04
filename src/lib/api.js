// src/lib/api.js

const API_BASE = process.env.REACT_APP_API_BASE;
const API_KEY = process.env.REACT_APP_API_KEY;
const DEVICE_ID = process.env.REACT_APP_DEVICE_ID || "esp32";

function authHeaders() {
  return API_KEY ? { Authorization: `Bearer ${API_KEY}` } : {};
}

async function getJSON(path) {
  if (!API_BASE) {
    throw new Error("REACT_APP_API_BASE is not set");
  }

  const res = await fetch(`${API_BASE}${path}`, {
    headers: {
      "Content-Type": "application/json",
      ...authHeaders(),
    },
  });

  if (!res.ok) {
    const text = await res.text();
    throw new Error(`GET ${path} ${res.status} ${text}`);
  }
  return res.json();
}

export const fetchLatest = (id = DEVICE_ID) =>
  getJSON(`/v1/devices/${encodeURIComponent(id)}/latest`);

export const fetchHistory = (id = DEVICE_ID, minutes = 360) =>
  getJSON(`/v1/devices/${encodeURIComponent(id)}/history?minutes=${minutes}`);
