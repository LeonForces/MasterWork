import { createContext, useContext, useEffect, useState } from "react";
import { api, getAccessToken, getRefreshToken, setAccessToken, setRefreshToken, UserInfo } from "./api";

type AuthContextValue = {
  user: UserInfo | null;
  loading: boolean;
  login: (username: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
};

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<UserInfo | null>(null);
  const [loading, setLoading] = useState(true);

  async function fetchMe(): Promise<void> {
    const token = getAccessToken();
    if (!token) {
      setUser(null);
      setLoading(false);
      return;
    }
    try {
      const response = await api.get<UserInfo>("/api/v1/auth/me");
      setUser(response.data);
    } catch {
      setAccessToken(null);
      setRefreshToken(null);
      setUser(null);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    fetchMe();
  }, []);

  async function login(username: string, password: string): Promise<void> {
    const response = await api.post("/api/v1/auth/login", { username, password });
    setAccessToken(response.data.access_token);
    setRefreshToken(response.data.refresh_token);
    const me = await api.get<UserInfo>("/api/v1/auth/me");
    setUser(me.data);
  }

  async function logout(): Promise<void> {
    const refreshToken = getRefreshToken();
    if (refreshToken) {
      await api.post("/api/v1/auth/logout", { refresh_token: refreshToken }).catch(() => undefined);
    }
    setAccessToken(null);
    setRefreshToken(null);
    setUser(null);
  }

  return <AuthContext.Provider value={{ user, loading, login, logout }}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) {
    throw new Error("useAuth must be used within AuthProvider");
  }
  return ctx;
}
