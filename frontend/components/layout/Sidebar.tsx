"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  BarChart3,
  Bell,
  Database,
  FilePlus,
  Inbox,
  LayoutDashboard,
  LogOut,
  ShieldCheck,
  Settings,
  Sparkles,
  Zap,
} from "lucide-react";
import { useAuth } from "@/contexts/AuthContext";

const navItems = [
  { href: "/dashboard", label: "Overview", icon: LayoutDashboard },
  { href: "/queue", label: "Complaint Queue", icon: Inbox },
  { href: "/new-complaint", label: "New Complaint", icon: FilePlus },
  { href: "/import", label: "Data Import", icon: Database },
  { href: "/operations", label: "Operations", icon: Settings },
  { href: "/insights", label: "Insights", icon: BarChart3 },
];

const adminNavItems = [
  { href: "/regulatory-rag", label: "Regulatory RAG", icon: ShieldCheck },
];

export function Sidebar() {
  const pathname = usePathname();
  const { user, logout } = useAuth();

  return (
    <aside className="fixed left-0 top-0 h-full w-[260px] bg-surface border-r border-outline-variant flex flex-col z-20">
      {/* Brand */}
      <div className="px-lg py-lg border-b border-outline-variant">
        <div className="flex items-center gap-sm">
          <div className="w-8 h-8 bg-primary rounded flex items-center justify-center">
            <Sparkles size={16} className="text-on-primary" />
          </div>
          <div>
            <p className="text-headline-sm font-semibold text-on-background leading-tight">
              CustomerPulse
            </p>
            <p className="text-label-md text-on-surface-variant uppercase tracking-wider">
              Ops Platform
            </p>
          </div>
        </div>
      </div>

      {/* Navigation */}
      <nav className="flex-1 overflow-y-auto py-sm px-sm" aria-label="Primary navigation">
        <div className="flex flex-col gap-xs">
          {[...navItems, ...(user?.role === "admin" ? adminNavItems : [])].map(({ href, label, icon: Icon }) => {
            const isActive =
              href === "/dashboard"
                ? pathname === "/dashboard" || pathname === "/"
                : pathname.startsWith(href);

            return (
              <Link
                key={href}
                href={href}
                className={`flex items-center gap-md px-md py-sm rounded text-label-md font-semibold transition-colors ${
                  isActive
                    ? "bg-secondary-container text-on-secondary-container"
                    : "text-on-surface-variant hover:bg-surface-container-low hover:text-on-surface"
                }`}
              >
                <Icon size={18} />
                <span>{label}</span>
              </Link>
            );
          })}
        </div>
      </nav>

      {/* Live indicator */}
      <div className="px-md py-sm border-t border-outline-variant">
        <div className="flex items-center gap-xs mb-xs">
          <Zap size={13} className="text-status-resolved" />
          <span className="text-label-md text-on-surface-variant">
            Real-time mode active
          </span>
        </div>
        <div className="flex items-center gap-xs">
          <Bell size={13} className="text-on-surface-variant" />
          <span className="text-label-md text-on-surface-variant">
            WebSocket: connected
          </span>
        </div>
      </div>

      {/* User section */}
      {user && (
        <div className="px-md py-md border-t border-outline-variant">
          <div className="flex items-center justify-between">
            <div className="min-w-0">
              <p className="text-body-sm font-semibold text-on-background truncate">
                {user.display_name}
              </p>
              <p className="text-label-md text-on-surface-variant capitalize">
                {user.role}
              </p>
            </div>
            <button
              onClick={logout}
              className="btn-icon shrink-0"
              title="Sign out"
              aria-label="Sign out"
            >
              <LogOut size={16} />
            </button>
          </div>
        </div>
      )}
    </aside>
  );
}
