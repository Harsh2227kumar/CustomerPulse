"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { login } from "@/lib/api/auth";
import { useAuth } from "@/contexts/AuthContext";

interface Credential {
  username: string;
  password: string;
  role: string;
}

const HINT_CREDENTIALS: Credential[] = [
  { username: "admin", password: "Admin@123", role: "Admin" },
  { username: "manager", password: "Manager@123", role: "Manager" },
  { username: "agent", password: "Agent@123", role: "Agent" },
];

export default function LoginPage() {
  const router = useRouter();
  const auth = useAuth();

  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Set document title
  useEffect(() => {
    document.title = "Sign In | CustomerPulse";
  }, []);

  // Redirect if already authenticated
  useEffect(() => {
    if (!auth.isLoading && auth.user) {
      router.replace("/dashboard");
    }
  }, [auth.isLoading, auth.user, router]);

  async function handleSubmit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    if (isSubmitting) return;

    setError(null);
    setIsSubmitting(true);

    try {
      const response = await login({ username: username.trim(), password });
      await auth.authenticate(response.api_key);
      router.replace("/dashboard");
    } catch (err: unknown) {
      const message =
        err instanceof Error
          ? err.message
          : "Invalid credentials. Please try again.";
      setError(message);
    } finally {
      setIsSubmitting(false);
    }
  }

  function fillCredential(cred: Credential) {
    setUsername(cred.username);
    setPassword(cred.password);
    setError(null);
  }

  // While auth is resolving from localStorage, show a full-page spinner
  if (auth.isLoading) {
    return (
      <div className="flex items-center justify-center min-h-[100dvh] w-full bg-background">
        <Spinner size="lg" />
      </div>
    );
  }

  // Redirect is in-flight — render nothing to avoid flash
  if (auth.user) return null;

  return (
    <div className="min-h-[100dvh] w-full flex bg-background text-on-background relative selection:bg-primary/10 selection:text-primary overflow-x-hidden">
      {/* ── Left Side Showcase (Hidden on mobile/tablet, visible on lg+) ── */}
      <div className="hidden lg:flex lg:w-1/2 xl:w-7/12 flex-col justify-between p-10 lg:p-14 xl:p-16 relative overflow-hidden bg-[#080d1a] text-white">
        {/* Ambient Gradients & Glows */}
        <div className="absolute inset-0 bg-gradient-to-br from-[#0f172a] via-[#080d1a] to-[#04070e] z-0" />
        <div className="absolute -top-32 -left-32 w-[550px] h-[550px] bg-blue-600/15 rounded-full blur-[130px] pointer-events-none" />
        <div className="absolute bottom-0 right-0 w-[450px] h-[450px] bg-indigo-500/10 rounded-full blur-[110px] pointer-events-none translate-y-1/4 translate-x-1/4" />
        
        {/* Subtle grid overlay */}
        <div className="absolute inset-0 bg-[linear-gradient(to_right,#ffffff07_1px,transparent_1px),linear-gradient(to_bottom,#ffffff07_1px,transparent_1px)] bg-[size:3.5rem_3.5rem] [mask-image:radial-gradient(ellipse_60%_50%_at_50%_50%,#000_70%,transparent_100%)] z-0" />

        {/* Brand Header */}
        <div className="relative z-10 flex items-center gap-3.5">
          <div className="flex items-center justify-center w-11 h-11 rounded-xl bg-gradient-to-tr from-blue-600 via-indigo-600 to-sky-400 text-white shadow-lg shadow-blue-500/25 ring-1 ring-white/20">
            <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2.5} strokeLinecap="round" strokeLinejoin="round" className="w-5 h-5">
              <polyline points="22 12 18 12 15 21 9 3 6 12 2 12" />
            </svg>
          </div>
          <div>
            <span className="text-xl font-bold tracking-tight text-white flex items-center gap-2">
              CustomerPulse
              <span className="text-[10px] uppercase tracking-widest px-2 py-0.5 rounded-full bg-blue-500/20 text-blue-300 font-semibold border border-blue-500/30">
                Enterprise
              </span>
            </span>
          </div>
        </div>

        {/* Center Content / Hero Pitch */}
        <div className="relative z-10 my-auto py-12 w-full max-w-[620px]">
          <div className="inline-flex items-center gap-2.5 px-3.5 py-1.5 rounded-full bg-blue-500/10 border border-blue-500/20 text-blue-300 text-xs font-medium mb-8 backdrop-blur-md shadow-sm">
            <span className="relative flex h-2 w-2">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
              <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-500"></span>
            </span>
            <span>AI Complaint Intelligence Engine v2.4 Online</span>
          </div>
          <h1 className="text-3xl lg:text-4xl xl:text-5xl font-extrabold tracking-tight text-white mb-6 leading-[1.18]">
            Turn customer friction into <span className="text-transparent bg-clip-text bg-gradient-to-r from-blue-400 via-indigo-300 to-sky-400">precision resolution</span>.
          </h1>
          <p className="text-slate-300 text-base lg:text-lg leading-relaxed mb-10 font-normal">
            Automated triaging, real-time sentiment telemetry, and instant regulatory compliance monitoring built for high-scale financial operations.
          </p>

          {/* Feature Highlight Cards */}
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 pt-6 border-t border-slate-800/80">
            <div className="rounded-xl bg-slate-900/70 border border-slate-800/80 p-4.5 backdrop-blur-md hover:border-blue-500/30 transition-colors">
              <div className="text-blue-400 font-mono text-2xl font-bold mb-1">99.4%</div>
              <div className="text-xs text-slate-400 font-medium">Triage Accuracy</div>
            </div>
            <div className="rounded-xl bg-slate-900/70 border border-slate-800/80 p-4.5 backdrop-blur-md hover:border-emerald-500/30 transition-colors">
              <div className="text-emerald-400 font-mono text-2xl font-bold mb-1">&lt; 1.2s</div>
              <div className="text-xs text-slate-400 font-medium">SLA Resolution Time</div>
            </div>
            <div className="rounded-xl bg-slate-900/70 border border-slate-800/80 p-4.5 backdrop-blur-md hover:border-indigo-500/30 transition-colors">
              <div className="text-indigo-400 font-mono text-2xl font-bold mb-1">24/7</div>
              <div className="text-xs text-slate-400 font-medium">Compliance Guard</div>
            </div>
          </div>
        </div>

        {/* Footer info */}
        <div className="relative z-10 flex flex-wrap items-center justify-between gap-4 text-xs text-slate-400 border-t border-slate-800/80 pt-6">
          <div className="flex items-center gap-4">
            <span>SOC2 Type II Certified</span>
            <span>•</span>
            <span>GDPR Compliant</span>
            <span>•</span>
            <span>ISO 27001</span>
          </div>
          <p>© {new Date().getFullYear()} CustomerPulse Inc.</p>
        </div>
      </div>

      {/* ── Right Side Form (Full width on mobile/tablet, 1/2 or 5/12 on lg+) ── */}
      <div className="w-full lg:w-1/2 xl:w-5/12 flex flex-col justify-center items-center min-h-[100dvh] px-4 sm:px-8 md:px-12 py-10 overflow-y-auto z-10 bg-background">
        <div className="w-full max-w-[420px] mx-auto my-auto flex flex-col justify-center">
          
          {/* Mobile-Only Brand Header */}
          <div className="lg:hidden mb-8 text-center flex flex-col items-center">
            <div className="inline-flex items-center gap-3 mb-2">
              <span className="flex items-center justify-center w-10 h-10 rounded-xl bg-gradient-to-tr from-blue-600 to-indigo-500 text-white shadow-md shadow-blue-500/20">
                <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2.5} strokeLinecap="round" strokeLinejoin="round" className="w-5 h-5">
                  <polyline points="22 12 18 12 15 21 9 3 6 12 2 12" />
                </svg>
              </span>
              <span className="text-2xl font-bold text-on-background tracking-tight">
                CustomerPulse
              </span>
            </div>
            <p className="text-xs text-on-surface-variant font-medium">
              AI-powered complaint intelligence platform
            </p>
          </div>

          {/* Login Card */}
          <div className="bg-surface rounded-2xl border border-outline-variant/80 shadow-xl shadow-slate-900/5 p-6 sm:p-8 transition-all">
            <div className="mb-6">
              <h2 className="text-xl sm:text-2xl font-bold text-on-surface tracking-tight mb-1.5">
                Sign in
              </h2>
              <p className="text-sm text-on-surface-variant">
                Enter your credentials to access your portal
              </p>
            </div>

            {/* Error Banner */}
            {error && (
              <div
                role="alert"
                className="mb-6 flex items-start gap-3 rounded-xl bg-error-container border border-error/20 p-3.5 text-on-error-container"
              >
                <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round" className="w-5 h-5 shrink-0 text-error mt-0.5">
                  <circle cx="12" cy="12" r="10" />
                  <line x1="12" y1="8" x2="12" y2="12" />
                  <line x1="12" y1="16" x2="12.01" y2="16" />
                </svg>
                <div className="text-sm font-medium leading-tight">{error}</div>
              </div>
            )}

            <form onSubmit={handleSubmit} className="flex flex-col gap-5" noValidate>
              {/* Username */}
              <div className="flex flex-col gap-1.5">
                <label htmlFor="username" className="text-xs font-semibold uppercase tracking-wider text-on-surface-variant">
                  Username
                </label>
                <div className="relative">
                  <input
                    id="username"
                    type="text"
                    autoComplete="username"
                    autoFocus
                    required
                    className="w-full h-11 px-3.5 rounded-xl border border-outline-variant bg-surface-container-lowest text-on-surface text-sm placeholder:text-on-surface-variant/60 focus:outline-none focus:border-primary focus:ring-4 focus:ring-primary/10 transition-all disabled:opacity-60 disabled:cursor-not-allowed"
                    placeholder="e.g. admin"
                    value={username}
                    onChange={(e) => setUsername(e.target.value)}
                    disabled={isSubmitting}
                  />
                </div>
              </div>

              {/* Password */}
              <div className="flex flex-col gap-1.5">
                <div className="flex items-center justify-between">
                  <label htmlFor="password" className="text-xs font-semibold uppercase tracking-wider text-on-surface-variant">
                    Password
                  </label>
                </div>
                <div className="relative">
                  <input
                    id="password"
                    type="password"
                    autoComplete="current-password"
                    required
                    className="w-full h-11 px-3.5 rounded-xl border border-outline-variant bg-surface-container-lowest text-on-surface text-sm placeholder:text-on-surface-variant/60 focus:outline-none focus:border-primary focus:ring-4 focus:ring-primary/10 transition-all disabled:opacity-60 disabled:cursor-not-allowed font-mono"
                    placeholder="••••••••"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    disabled={isSubmitting}
                  />
                </div>
              </div>

              {/* Submit */}
              <button
                type="submit"
                className="w-full h-11 mt-1 rounded-xl bg-primary hover:bg-primary/90 active:scale-[0.99] text-on-primary font-semibold text-sm shadow-md shadow-primary/15 transition-all duration-150 flex items-center justify-center gap-2 disabled:opacity-50 disabled:pointer-events-none cursor-pointer"
                disabled={isSubmitting || !username.trim() || !password}
              >
                {isSubmitting ? (
                  <>
                    <Spinner size="sm" />
                    <span>Signing in…</span>
                  </>
                ) : (
                  <span>Sign In</span>
                )}
              </button>
            </form>
          </div>

          {/* Demo Credentials Hint */}
          <div className="mt-6 rounded-2xl border border-outline-variant bg-surface-container-low/60 p-5 sm:p-6 shadow-sm">
            <div className="flex items-center gap-2 mb-3.5">
              <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round" className="w-4 h-4 text-primary">
                <path d="M12 2v20M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6" />
              </svg>
              <p className="text-xs font-bold uppercase tracking-wider text-on-surface-variant">
                Demo Accounts (Click to auto-fill)
              </p>
            </div>

            <div className="flex flex-col gap-2.5">
              {HINT_CREDENTIALS.map((cred) => (
                <button
                  key={cred.role}
                  type="button"
                  onClick={() => fillCredential(cred)}
                  className="group relative flex flex-col sm:flex-row sm:items-center justify-between gap-2 sm:gap-4 rounded-xl border border-outline-variant bg-surface p-3 sm:px-3.5 sm:py-2.5 hover:border-primary/40 hover:shadow-md hover:-translate-y-0.5 active:translate-y-0 transition-all duration-150 text-left cursor-pointer"
                >
                  <div className="flex items-center gap-3 min-w-0">
                    <RoleBadge role={cred.role} />
                    <div className="min-w-0 truncate">
                      <p className="text-xs sm:text-sm font-semibold text-on-surface truncate">
                        {cred.username}
                      </p>
                      <p className="text-[11px] sm:text-xs text-on-surface-variant font-mono truncate">
                        {cred.password}
                      </p>
                    </div>
                  </div>
                  
                  <div className="flex items-center justify-end self-end sm:self-center shrink-0">
                    <span className="inline-flex items-center gap-1 text-[11px] font-medium text-primary bg-primary/5 px-2 py-1 rounded-md group-hover:bg-primary group-hover:text-on-primary transition-colors">
                      <span>Use</span>
                      <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round" className="w-3 h-3 group-hover:translate-x-0.5 transition-transform">
                        <line x1="5" y1="12" x2="19" y2="12" />
                        <polyline points="12 5 19 12 12 19" />
                      </svg>
                    </span>
                  </div>
                </button>
              ))}
            </div>
          </div>

          <div className="mt-8 text-center lg:hidden">
            <p className="text-xs text-on-surface-variant">
              © {new Date().getFullYear()} CustomerPulse. All rights reserved.
            </p>
          </div>

        </div>
      </div>
    </div>
  );
}

// ── Helpers ────────────────────────────────────────────────────────────────────

function Spinner({ size = "md" }: { size?: "sm" | "md" | "lg" }) {
  const sizeClass =
    size === "sm" ? "w-4 h-4" : size === "lg" ? "w-8 h-8" : "w-5 h-5";
  return (
    <svg
      className={`${sizeClass} animate-spin text-current`}
      xmlns="http://www.w3.org/2000/svg"
      fill="none"
      viewBox="0 0 24 24"
      aria-hidden="true"
    >
      <circle
        className="opacity-25"
        cx="12"
        cy="12"
        r="10"
        stroke="currentColor"
        strokeWidth="4"
      />
      <path
        className="opacity-75"
        fill="currentColor"
        d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"
      />
    </svg>
  );
}

function RoleBadge({ role }: { role: string }) {
  const badgeStyles: Record<string, string> = {
    Admin: "bg-blue-50 text-blue-700 border-blue-200 dark:bg-blue-950/60 dark:text-blue-300 dark:border-blue-800",
    Manager: "bg-amber-50 text-amber-700 border-amber-200 dark:bg-amber-950/60 dark:text-amber-300 dark:border-amber-800",
    Agent: "bg-emerald-50 text-emerald-700 border-emerald-200 dark:bg-emerald-950/60 dark:text-emerald-300 dark:border-emerald-800",
  };
  const cls = badgeStyles[role] ?? "bg-slate-100 text-slate-700 border-slate-200";
  return (
    <span
      className={`inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-semibold tracking-wide shrink-0 ${cls}`}
    >
      {role}
    </span>
  );
}
