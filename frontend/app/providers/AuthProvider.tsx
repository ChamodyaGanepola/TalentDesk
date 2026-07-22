"use client";

import {
  AuthUser,
  fetchCurrentUser,
  getStoredUser,
  logoutSession,
  setSession,
} from "@/app/lib/auth";
import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
} from "react";

type AuthContextValue = {
  user: AuthUser | null;
  loading: boolean;
  isAuthenticated: boolean;
  login: (accessToken: string, refreshToken: string, user: AuthUser) => void;
  logout: () => Promise<void>;
  refreshUser: () => Promise<AuthUser | null>;
};

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<AuthUser | null>(null);
  const [loading, setLoading] = useState(true);

  const refreshUser = useCallback(async () => {
    const current = await fetchCurrentUser();
    setUser(current);
    return current;
  }, []);

  useEffect(() => {
    let active = true;

    async function bootstrap() {
      const cached = getStoredUser();
      if (cached) {
        setUser(cached);
      }

      const verified = await fetchCurrentUser();
      if (!active) return;

      setUser(verified);
      setLoading(false);
    }

    void bootstrap();

    return () => {
      active = false;
    };
  }, []);

  const login = useCallback(
    (accessToken: string, refreshToken: string, nextUser: AuthUser) => {
      setSession(accessToken, refreshToken, nextUser);
      setUser(nextUser);
    },
    []
  );

  const logout = useCallback(async () => {
    await logoutSession();
    setUser(null);
  }, []);

  const value = useMemo(
    () => ({
      user,
      loading,
      isAuthenticated: Boolean(user),
      login,
      logout,
      refreshUser,
    }),
    [user, loading, login, logout, refreshUser]
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used within AuthProvider");
  }
  return context;
}

export function useAuthOptional() {
  return useContext(AuthContext);
}
