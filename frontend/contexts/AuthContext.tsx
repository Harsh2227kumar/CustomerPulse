"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useState,
  type ReactNode,
} from "react";
import { getMe } from "@/lib/api/auth";
import { clearApiKey, getApiKey, setApiKey } from "@/lib/api/client";
import type { UserProfile } from "@/lib/api/types";

// ── Types ────────────────────────────────────────────────────────────────────

interface AuthContextValue {
  user: UserProfile | null;
  apiKey: string;
  isLoading: boolean;
  /** Set a new API key and immediately fetch the user profile. */
  authenticate: (key: string) => Promise<void>;
  logout: () => void;
}

// ── Context ──────────────────────────────────────────────────────────────────

const AuthContext = createContext<AuthContextValue | null>(null);

// ── Provider ─────────────────────────────────────────────────────────────────

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<UserProfile | null>(null);
  const [apiKey, setKeyState] = useState<string>("");
  const [isLoading, setIsLoading] = useState(true);

  const fetchUser = useCallback(async (key: string) => {
    if (!key) {
      setUser(null);
      setIsLoading(false);
      return;
    }
    try {
      setApiKey(key);
      setKeyState(key);
      const profile = await getMe();
      setUser(profile);
    } catch {
      clearApiKey();
      setKeyState("");
      setUser(null);
    } finally {
      setIsLoading(false);
    }
  }, []);

  // Restore session from localStorage on mount
  useEffect(() => {
    const storedKey = getApiKey();
    if (storedKey) {
      void fetchUser(storedKey);
    } else {
      setIsLoading(false);
    }
  }, [fetchUser]);

  const authenticate = useCallback(
    async (key: string) => {
      setIsLoading(true);
      await fetchUser(key);
    },
    [fetchUser]
  );

  const logout = useCallback(() => {
    clearApiKey();
    setKeyState("");
    setUser(null);
  }, []);

  return (
    <AuthContext.Provider value={{ user, apiKey, isLoading, authenticate, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

// ── Hook ─────────────────────────────────────────────────────────────────────

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) {
    throw new Error("useAuth must be used inside <AuthProvider>");
  }
  return ctx;
}
