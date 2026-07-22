"use client";

import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { Loader2 } from "lucide-react";
import { useToast } from "@/app/components/ui/Toast";
import {
  clearRememberedEmail,
  getRememberedEmail,
  setRememberedEmail,
} from "@/app/lib/auth";
import { useAuth } from "@/app/providers/AuthProvider";

import { getApiBase, apiFetch, apiHeaders } from "@/app/lib/api";

export default function LoginPage() {
  const router = useRouter();
  const { showToast } = useToast();
  const { login, isAuthenticated, loading: authLoading } = useAuth();

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [rememberMe, setRememberMe] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    const savedEmail = getRememberedEmail();
    if (savedEmail) {
      setEmail(savedEmail);
      setRememberMe(true);
    }
  }, []);

  useEffect(() => {
    if (!authLoading && isAuthenticated) {
      router.replace("/dashboard");
    }
  }, [authLoading, isAuthenticated, router]);

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setLoading(true);

    try {
      if (!getApiBase()) {
        setError("API URL is not configured. Set NEXT_PUBLIC_API_URL in your environment.");
        return;
      }

      const res = await apiFetch("/auth/login", {
        method: "POST",
        headers: apiHeaders({ "Content-Type": "application/json" }),
        body: JSON.stringify({ email, password }),
      });

      if (!res) {
        setError("Cannot reach the server. Check that the backend is running.");
        return;
      }

      let data: {
        success?: boolean;
        message?: string;
        access_token?: string;
        refresh_token?: string;
        user?: { name: string; email: string };
      } = {};

      try {
        data = await res.json();
      } catch {
        setError("Invalid response from server. Please try again.");
        return;
      }

      if (!res.ok || !data.success) {
        setError(data.message || "Invalid credentials.");
        return;
      }

      if (!data.access_token || !data.refresh_token || !data.user) {
        setError("Login succeeded but session tokens were not returned.");
        return;
      }

      if (rememberMe) {
        setRememberedEmail(email);
      } else {
        clearRememberedEmail();
      }

      login(data.access_token, data.refresh_token, data.user);
      showToast("Welcome back!", "success");
      router.push("/dashboard");
    } catch {
      setError("Server error. Please try again.");
    } finally {
      setLoading(false);
    }
  };

  if (authLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-slate-100">
        <Loader2 className="h-8 w-8 animate-spin text-cyan-600" />
      </div>
    );
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-slate-100 px-4">
      <div className="w-full max-w-md bg-white p-8 rounded-3xl shadow-xl">
        <div className="flex justify-center mb-6">
          <img
            src="/MedcubeUSA.png"
            alt="MedcubeUSALogo"
            className="h-20 w-auto object-contain"
          />
        </div>

        <h1 className="text-3xl font-bold text-center text-slate-800">
          TalentDesk
        </h1>

        <p className="text-center text-slate-500 mt-2 mb-8">
          Sign in to continue
        </p>

        <form onSubmit={handleLogin} className="space-y-5">
          {error && (
            <div className="bg-red-50 border border-red-200 text-red-700 text-sm rounded-xl px-4 py-3">
              {error}
            </div>
          )}

          <div>
            <label className="block text-sm mb-2 text-slate-600">
              Email Address
            </label>
            <input
              type="email"
              placeholder="enter your email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="w-full border border-slate-300 rounded-xl px-4 py-3 focus:outline-none focus:ring-2 focus:ring-cyan-50 text-black"
              required
            />
          </div>

          <div>
            <label className="block text-sm mb-2 text-slate-600">
              Password
            </label>
            <input
              type="password"
              placeholder="enter your password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="w-full border border-slate-300 rounded-xl px-4 py-3 focus:outline-none focus:ring-2 focus:ring-cyan-50 text-black"
              required
            />
          </div>

          <div className="flex items-center gap-2 text-sm text-slate-600">
            <input
              type="checkbox"
              checked={rememberMe}
              onChange={(e) => setRememberMe(e.target.checked)}
            />
            Remember Me
          </div>

          <button
            type="submit"
            disabled={loading}
            className="w-full bg-cyan-600 hover:bg-cyan-700 text-white py-3 rounded-xl font-semibold transition disabled:opacity-60 inline-flex items-center justify-center gap-2"
          >
            {loading && <Loader2 size={18} className="animate-spin" />}
            {loading ? "Signing in..." : "Sign In"}
          </button>
        </form>
      </div>
    </div>
  );
}
