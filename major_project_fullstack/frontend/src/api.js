const API_BASE = import.meta.env.VITE_API_URL || "http://localhost:8080";

async function request(path, { method = "GET", token, body, formData } = {}) {
  const headers = {};
  if (token) {
    headers.Authorization = `Bearer ${token}`;
  }
  if (body) {
    headers["Content-Type"] = "application/json";
  }

  const response = await fetch(`${API_BASE}${path}`, {
    method,
    headers,
    body: formData || (body ? JSON.stringify(body) : undefined)
  });

  const payload = await response.json().catch(() => ({}));
  if (!response.ok) {
    const isAuthFailure = response.status === 401 || response.status === 403;
    const message = isAuthFailure
      ? "Session expired. Please login again."
      : payload.error || payload.details || "Request failed";
    const error = new Error(message);
    error.status = response.status;
    error.payload = payload;
    throw error;
  }
  return payload;
}

export function registerUser(data) {
  return request("/api/auth/register", { method: "POST", body: data });
}

export function loginUser(data) {
  return request("/api/auth/login", { method: "POST", body: data });
}

export function fetchProfile(token) {
  return request("/api/auth/profile", { token });
}

export function fetchSummary(token) {
  return request("/api/dashboard/summary", { token });
}

export function fetchServices(token) {
  return request("/api/services", { token });
}

export function fetchVideos(token) {
  return request("/api/videos", { token });
}

export function fetchJobs(token) {
  return request("/api/analysis/jobs", { token });
}

export function fetchLiveStatus(token) {
  return request("/api/live/status", { token });
}

export function fetchLiveAlerts(token, limit = 30) {
  return request(`/api/live/alerts?limit=${limit}`, { token });
}

export function fetchJob(token, jobId) {
  return request(`/api/analysis/jobs/${jobId}`, { token });
}

export function uploadVideo(token, file) {
  const formData = new FormData();
  formData.append("file", file);
  return request("/api/videos/upload", {
    method: "POST",
    token,
    formData
  });
}

export function runAnalysis(token, payload) {
  return request("/api/analysis/run", {
    method: "POST",
    token,
    body: payload
  });
}

export async function fetchJobOutputUrl(token, jobId) {
  const response = await fetch(`${API_BASE}/api/analysis/jobs/${jobId}/output`, {
    method: "GET",
    headers: {
      Authorization: `Bearer ${token}`
    }
  });
  if (!response.ok) {
    const text = await response.text();
    let payload = {};
    try {
      payload = JSON.parse(text);
    } catch {
      payload = {};
    }
    throw new Error(
      payload.error ||
      payload.details ||
      text ||
      `Unable to load output video (HTTP ${response.status})`
    );
  }
  const blob = await response.blob();
  return URL.createObjectURL(blob);
}
