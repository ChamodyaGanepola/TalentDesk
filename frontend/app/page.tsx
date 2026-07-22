"use client";

import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { Loader2 } from "lucide-react";
import { useToast } from "@/app/components/ui/Toast";

export default function LoginPage() {
  const router = useRouter();
  const { showToast } = useToast();

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [rememberMe, setRememberMe] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  
  useEffect(() => {
    const savedEmail = localStorage.getItem("remember_email");
    const savedPassword = localStorage.getItem("remember_password");

    if (savedEmail && savedPassword) {
      setEmail(savedEmail);
      setPassword(savedPassword);
      setRememberMe(true);
    }
  }, []);

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setLoading(true);

    try {
      const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/auth/login`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json", "ngrok-skip-browser-warning": "true",
        },
        body: JSON.stringify({ email, password }),
      });

      const data = await res.json();

      //  backend failed login
      if (!res.ok || !data.success) {
        setError(data.message || "Login failed. Please check your credentials.");
        return;
      }

      // ✅ remember me
      if (rememberMe) {
        localStorage.setItem("remember_email", email);
        localStorage.setItem("remember_password", password);
      } else {
        localStorage.removeItem("remember_email");
        localStorage.removeItem("remember_password");
      }

      localStorage.setItem("user", JSON.stringify(data.user));

      showToast("Welcome back!", "success");
      router.push("/dashboard");
    } catch (err) {
      setError("Server error. Please try again.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-slate-100 px-4">
      <div className="w-full max-w-md bg-white p-8 rounded-3xl shadow-xl">
        {/* Logo */}
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