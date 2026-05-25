import axios from "axios";

export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";

export const api = axios.create({
  baseURL: API_BASE_URL
});

let refreshPromise: Promise<string | null> | null = null;

export type UserInfo = {
  user_id: string;
  username: string;
  roles: string[];
  is_active: boolean;
};

export type LoginResponse = {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in_seconds: number;
  roles: string[];
};

export function setAccessToken(token: string | null): void {
  if (token) {
    localStorage.setItem("access_token", token);
  } else {
    localStorage.removeItem("access_token");
  }
}

export function setRefreshToken(token: string | null): void {
  if (token) {
    localStorage.setItem("refresh_token", token);
  } else {
    localStorage.removeItem("refresh_token");
  }
}

export function getAccessToken(): string | null {
  return localStorage.getItem("access_token");
}

export function getRefreshToken(): string | null {
  return localStorage.getItem("refresh_token");
}

function clearTokens(): void {
  setAccessToken(null);
  setRefreshToken(null);
}

async function refreshAccessToken(): Promise<string | null> {
  const refreshToken = getRefreshToken();
  if (!refreshToken) {
    clearTokens();
    return null;
  }
  try {
    const response = await axios.post<LoginResponse>(`${API_BASE_URL}/api/v1/auth/refresh`, {
      refresh_token: refreshToken
    });
    setAccessToken(response.data.access_token);
    setRefreshToken(response.data.refresh_token);
    return response.data.access_token;
  } catch {
    clearTokens();
    return null;
  }
}

api.interceptors.request.use((config) => {
  const token = getAccessToken();
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error?.config as
      | (Record<string, unknown> & { headers?: Record<string, string>; url?: string })
      | undefined;
    const statusCode = error?.response?.status as number | undefined;

    if (!originalRequest || statusCode !== 401) {
      throw error;
    }
    if (originalRequest.url?.includes("/api/v1/auth/login") || originalRequest.url?.includes("/api/v1/auth/refresh")) {
      throw error;
    }
    if (originalRequest._retry) {
      throw error;
    }

    originalRequest._retry = true;
    if (!refreshPromise) {
      refreshPromise = refreshAccessToken().finally(() => {
        refreshPromise = null;
      });
    }
    const newAccessToken = await refreshPromise;
    if (!newAccessToken) {
      throw error;
    }

    originalRequest.headers = originalRequest.headers ?? {};
    originalRequest.headers.Authorization = `Bearer ${newAccessToken}`;
    return api(originalRequest);
  }
);
