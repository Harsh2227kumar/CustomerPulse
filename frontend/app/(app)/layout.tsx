"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/contexts/AuthContext";
import { Sidebar } from "@/components/layout/Sidebar";
import { TopBar } from "@/components/layout/TopBar";

// ── Full-page loading spinner ─────────────────────────────────────────────────

function FullPageSpinner() {
  return (
    <div
      className="flex items-center justify-center min-h-screen bg-background"
      role="status"
      aria-label="Loading application"
    >
      <div className="flex flex-col items-center gap-md">
        <svg
          className="w-8 h-8 animate-spin text-primary"
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
        <p className="text-body-sm text-on-surface-variant">Loading…</p>
      </div>
    </div>
  );
}

// ── App Shell Layout ──────────────────────────────────────────────────────────

export default function AppLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const auth = useAuth();
  const router = useRouter();

  // Guard: redirect unauthenticated users to login
  useEffect(() => {
    if (!auth.isLoading && !auth.user) {
      router.replace("/login");
    }
  }, [auth.isLoading, auth.user, router]);

  // Show spinner while auth context is resolving
  if (auth.isLoading) {
    return <FullPageSpinner />;
  }

  // Don't render the shell while redirect is in-flight
  if (!auth.user) {
    return <FullPageSpinner />;
  }

  return (
    <div className="flex min-h-screen">
      {/* ── Sidebar — fixed, full height ─────────────────────────────────── */}
      <aside className="fixed inset-y-0 left-0 w-[260px] z-30">
        <Sidebar />
      </aside>

      {/* ── Main content area — offset by sidebar width ───────────────────── */}
      <div className="flex-1 pl-[260px] flex flex-col min-h-screen">
        {/* TopBar — sticky at top */}
        <header className="sticky top-0 z-20 h-16">
          <TopBar />
        </header>

        {/* Page content */}
        <main className="flex-1 overflow-auto bg-background p-lg">
          {children}
        </main>
      </div>
    </div>
  );
}
