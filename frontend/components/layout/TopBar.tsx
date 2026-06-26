"use client";

import { useState } from "react";
import { Bell, Key, RefreshCw, Search, ShieldCheck, Wifi, WifiOff } from "lucide-react";
import { useAuth } from "@/contexts/AuthContext";
import { useWebSocket } from "@/lib/hooks/useWebSocket";

interface TopBarProps {
  search?: string;
  onSearchChange?: (value: string) => void;
  onRefresh?: () => void;
}

export function TopBar({ search, onSearchChange, onRefresh }: TopBarProps) {
  const { user } = useAuth();
  const { status: wsStatus } = useWebSocket();
  const [showKeyModal, setShowKeyModal] = useState(false);

  const WsIcon = wsStatus === "live" ? Wifi : WifiOff;
  const wsColor =
    wsStatus === "live"
      ? "text-status-resolved"
      : wsStatus === "connecting"
      ? "text-status-pending"
      : "text-error";

  return (
    <header className="h-16 bg-surface-container-lowest border-b border-outline-variant flex items-center justify-between px-lg gap-md sticky top-0 z-10">
      {/* Search */}
      <div className="flex items-center gap-xs bg-surface-container-low border border-outline-variant rounded w-96 max-w-full px-sm">
        <Search size={16} className="text-on-surface-variant shrink-0" />
        <input
          type="text"
          value={search ?? ""}
          onChange={(e) => onSearchChange?.(e.target.value)}
          placeholder="Search complaints, IDs…"
          className="bg-transparent border-none outline-none text-body-sm text-on-surface placeholder:text-on-surface-variant w-full py-xs"
          aria-label="Search complaints"
        />
      </div>

      {/* Actions */}
      <div className="flex items-center gap-sm">
        {/* Status indicators */}
        <div className="hidden lg:flex items-center gap-md mr-sm">
          <div className="flex items-center gap-xs">
            <span className="w-2 h-2 rounded-full bg-status-resolved inline-block" />
            <span className="text-label-md text-on-surface-variant uppercase">
              API
            </span>
          </div>
          <div className="flex items-center gap-xs">
            <WsIcon size={14} className={wsColor} />
            <span className="text-label-md text-on-surface-variant uppercase">
              {wsStatus === "live" ? "Live" : wsStatus === "connecting" ? "Connecting" : "Offline"}
            </span>
          </div>
        </div>

        <div className="h-4 w-px bg-outline-variant" />

        {onRefresh && (
          <button
            onClick={onRefresh}
            className="btn-icon"
            title="Refresh data"
            aria-label="Refresh"
          >
            <RefreshCw size={18} />
          </button>
        )}

        <button className="btn-icon" title="Notifications" aria-label="Notifications">
          <Bell size={18} />
        </button>

        <button
          onClick={() => setShowKeyModal(true)}
          className="btn-icon"
          title="API Key"
          aria-label="API Key settings"
        >
          <Key size={18} />
        </button>

        {/* User avatar */}
        <div className="w-8 h-8 rounded-full bg-primary flex items-center justify-center text-on-primary text-label-md font-bold select-none ml-xs">
          {user?.display_name?.[0]?.toUpperCase() ?? "U"}
        </div>
      </div>

      {/* API Key modal */}
      {showKeyModal && (
        <ApiKeyModal onClose={() => setShowKeyModal(false)} />
      )}
    </header>
  );
}

// ── Inline API Key Modal ──────────────────────────────────────────────────────

function ApiKeyModal({ onClose }: { onClose: () => void }) {
  const { authenticate, apiKey } = useAuth();
  const [value, setValue] = useState(apiKey);
  const [saving, setSaving] = useState(false);

  async function handleSave() {
    if (!value.trim()) return;
    setSaving(true);
    try {
      await authenticate(value.trim());
      onClose();
    } finally {
      setSaving(false);
    }
  }

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-sm"
      onClick={onClose}
    >
      <div
        className="card w-96 shadow-modal p-lg"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center gap-sm mb-md">
          <ShieldCheck size={20} className="text-primary" />
          <h2 className="text-headline-sm font-semibold text-on-background">
            API Key
          </h2>
        </div>
        <p className="text-body-sm text-on-surface-variant mb-md">
          Enter your Bearer API key. Keys are configured in the backend{" "}
          <code className="font-mono text-body-sm">.env</code>.
        </p>
        <label className="form-label" htmlFor="api-key-input">Bearer key</label>
        <input
          id="api-key-input"
          type="password"
          value={value}
          onChange={(e) => setValue(e.target.value)}
          className="form-input mb-lg"
          placeholder="cp_admin_key_…"
          autoComplete="off"
        />
        <div className="flex gap-sm justify-end">
          <button onClick={onClose} className="btn-secondary">
            Cancel
          </button>
          <button
            onClick={handleSave}
            className="btn-primary"
            disabled={saving || !value.trim()}
          >
            {saving ? "Saving…" : "Save & verify"}
          </button>
        </div>
      </div>
    </div>
  );
}
