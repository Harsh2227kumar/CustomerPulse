"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import {
  Activity,
  Ban,
  Building2,
  CheckCircle2,
  Download,
  History,
  KeyRound,
  Loader2,
  Plus,
  RefreshCw,
  Search,
  ShieldCheck,
  UserPlus,
  Users,
} from "lucide-react";
import {
  activateEmployee,
  createDepartment,
  createEmployee,
  downloadDepartmentReport,
  downloadEmployeePerformanceReport,
  getAdminDashboard,
  listAuditLogs,
  listDepartments,
  listEmployees,
  listLoginHistory,
  resetEmployeePassword,
  suspendEmployee,
  updateEmployee,
} from "@/lib/api/admin";
import type {
  AdminDashboardResponse,
  AuditLogEntry,
  DepartmentRead,
  EmployeeCreateRequest,
  EmployeeRead,
  EmployeeRole,
  EmployeeStatus,
  LoginHistoryEntry,
} from "@/lib/api/types";
import { Badge } from "@/components/ui/Badge";
import { LoadingSpinner } from "@/components/ui/LoadingSpinner";
import { Modal } from "@/components/ui/Modal";
import { formatDateTime, humanize, triggerBlobDownload, type BadgeVariant } from "@/lib/utils/format";

type Tab = "employees" | "departments" | "audit" | "reports";

const roles: EmployeeRole[] = ["agent", "manager", "admin", "super_admin"];
const statuses: EmployeeStatus[] = ["active", "suspended", "inactive"];

const emptyEmployeeForm: EmployeeCreateRequest = {
  name: "",
  email: "",
  password: "",
  role: "agent",
  department_id: null,
  reports_to: null,
};

export default function AdminPage() {
  const [tab, setTab] = useState<Tab>("employees");
  const [dashboard, setDashboard] = useState<AdminDashboardResponse | null>(null);
  const [employees, setEmployees] = useState<EmployeeRead[]>([]);
  const [departments, setDepartments] = useState<DepartmentRead[]>([]);
  const [auditLogs, setAuditLogs] = useState<AuditLogEntry[]>([]);
  const [loginHistory, setLoginHistory] = useState<LoginHistoryEntry[]>([]);
  const [search, setSearch] = useState("");
  const [roleFilter, setRoleFilter] = useState<EmployeeRole | "">("");
  const [statusFilter, setStatusFilter] = useState<EmployeeStatus | "">("");
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [employeeModal, setEmployeeModal] = useState<EmployeeRead | "new" | null>(null);
  const [tempPassword, setTempPassword] = useState<{ employee: string; password: string } | null>(null);

  const reload = useCallback(async (soft = false) => {
    if (soft) setRefreshing(true); else setLoading(true);
    setError(null);
    try {
      const [dash, emp, dept, audit, logins] = await Promise.all([
        getAdminDashboard(),
        listEmployees({ limit: 100, search: search || undefined, role: roleFilter || undefined, status: statusFilter || undefined }),
        listDepartments({ limit: 100 }),
        listAuditLogs({ limit: 25 }),
        listLoginHistory({ limit: 25 }),
      ]);
      setDashboard(dash);
      setEmployees(emp.items);
      setDepartments(dept.items);
      setAuditLogs(audit.items);
      setLoginHistory(logins.items);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load admin console");
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, [roleFilter, search, statusFilter]);

  useEffect(() => { void reload(); }, [reload]);

  const departmentById = useMemo(() => new Map(departments.map((d) => [d.id, d])), [departments]);
  const employeeById = useMemo(() => new Map(employees.map((e) => [e.id, e])), [employees]);

  async function handleEmployeeSaved() {
    setEmployeeModal(null);
    await reload(true);
  }

  async function handleStatus(employee: EmployeeRead) {
    try {
      if (employee.status === "active") {
        const reason = window.prompt(`Reason to suspend ${employee.name}?`, "Administrative action");
        if (!reason) return;
        await suspendEmployee(employee.employee_id, reason);
      } else {
        await activateEmployee(employee.employee_id);
      }
      await reload(true);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Employee status update failed");
    }
  }

  async function handleResetPassword(employee: EmployeeRead) {
    try {
      const result = await resetEmployeePassword(employee.employee_id);
      setTempPassword({ employee: employee.name, password: result.temporary_password });
      await reload(true);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Password reset failed");
    }
  }

  if (loading) return <LoadingSpinner fullPage label="Loading admin console..." />;

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
      <div className="page-header">
        <div>
          <h1 className="page-title">Admin Console</h1>
          <p className="page-subtitle">Employee access, departments, audit trail, login history, and admin CSV reports.</p>
        </div>
        <button className="btn-secondary" onClick={() => reload(true)} disabled={refreshing}>
          <RefreshCw size={14} className={refreshing ? "animate-spin" : ""} />Refresh
        </button>
      </div>

      {error && <div className="alert-error">{error}</div>}

      {dashboard && <DashboardStrip dashboard={dashboard} />}

      <div className="tab-bar">
        <TabButton active={tab === "employees"} onClick={() => setTab("employees")} icon={<Users size={14} />} label="Employees" />
        <TabButton active={tab === "departments"} onClick={() => setTab("departments")} icon={<Building2 size={14} />} label="Departments" />
        <TabButton active={tab === "audit"} onClick={() => setTab("audit")} icon={<History size={14} />} label="Audit & Login History" />
        <TabButton active={tab === "reports"} onClick={() => setTab("reports")} icon={<Download size={14} />} label="Reports" />
      </div>

      {tab === "employees" && (
        <div className="card">
          <div className="card-header" style={{ gap: 12, flexWrap: "wrap" }}>
            <div style={{ display: "flex", alignItems: "center", gap: 8 }}><Users size={16} /><span style={{ fontWeight: 700 }}>Employees</span><Badge>{employees.length} shown</Badge></div>
            <div style={{ display: "flex", gap: 8, flexWrap: "wrap", alignItems: "center" }}>
              <div style={{ position: "relative", width: 220 }}>
                <Search size={14} style={{ position: "absolute", left: 8, top: 10, color: "var(--color-on-surface-variant)" }} />
                <input className="form-input" value={search} onChange={(e) => setSearch(e.target.value)} placeholder="Search name or email" style={{ paddingLeft: 28 }} />
              </div>
              <select className="form-select" value={roleFilter} onChange={(e) => setRoleFilter(e.target.value as EmployeeRole | "")} style={{ width: 140 }}>
                <option value="">All roles</option>{roles.map((r) => <option key={r} value={r}>{humanize(r)}</option>)}
              </select>
              <select className="form-select" value={statusFilter} onChange={(e) => setStatusFilter(e.target.value as EmployeeStatus | "")} style={{ width: 130 }}>
                <option value="">All status</option>{statuses.map((s) => <option key={s} value={s}>{humanize(s)}</option>)}
              </select>
              <button className="btn-primary" onClick={() => setEmployeeModal("new")}><UserPlus size={14} />New Employee</button>
            </div>
          </div>
          <div style={{ overflowX: "auto" }}>
            <table className="data-table">
              <thead><tr><th>Employee</th><th>Role</th><th>Status</th><th>Department</th><th>Manager</th><th>Updated</th><th>Actions</th></tr></thead>
              <tbody>
                {employees.map((employee) => (
                  <tr key={employee.id}>
                    <td><strong>{employee.name}</strong><div className="id-pill">{employee.employee_id}</div><div style={{ color: "var(--color-on-surface-variant)", fontSize: 12 }}>{employee.email}</div></td>
                    <td><Badge variant={roleVariant(employee.role)}>{humanize(employee.role)}</Badge></td>
                    <td><Badge variant={statusVariant(employee.status)}>{humanize(employee.status)}</Badge></td>
                    <td>{employee.department_id ? departmentById.get(employee.department_id)?.name ?? employee.department_id : "-"}</td>
                    <td>{employee.reports_to ? employeeById.get(employee.reports_to)?.name ?? employee.reports_to : "-"}</td>
                    <td>{formatDateTime(employee.updated_at)}</td>
                    <td>
                      <div style={{ display: "flex", gap: 6, flexWrap: "wrap" }}>
                        <button className="btn-secondary" onClick={() => setEmployeeModal(employee)}>Edit</button>
                        <button className={employee.status === "active" ? "btn-danger" : "btn-secondary"} onClick={() => handleStatus(employee)}>{employee.status === "active" ? <Ban size={13} /> : <CheckCircle2 size={13} />}{employee.status === "active" ? "Suspend" : "Activate"}</button>
                        <button className="btn-secondary" onClick={() => handleResetPassword(employee)}><KeyRound size={13} />Reset</button>
                      </div>
                    </td>
                  </tr>
                ))}
                {!employees.length && <tr><td colSpan={7} style={{ color: "var(--color-on-surface-variant)", textAlign: "center", padding: 24 }}>No employees match the current filters.</td></tr>}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {tab === "departments" && <DepartmentsPanel departments={departments} onChanged={() => reload(true)} />}
      {tab === "audit" && <AuditPanel auditLogs={auditLogs} loginHistory={loginHistory} />}
      {tab === "reports" && <ReportsPanel />}

      {employeeModal && (
        <EmployeeModal
          employee={employeeModal === "new" ? null : employeeModal}
          departments={departments}
          employees={employees}
          onClose={() => setEmployeeModal(null)}
          onSaved={handleEmployeeSaved}
        />
      )}

      {tempPassword && (
        <Modal title="Temporary Password" onClose={() => setTempPassword(null)}>
          <p style={{ marginBottom: 12 }}>Share this password with <strong>{tempPassword.employee}</strong>. It will not be shown again.</p>
          <code className="id-pill" style={{ maxWidth: "100%", fontSize: 14, padding: 8 }}>{tempPassword.password}</code>
        </Modal>
      )}
    </div>
  );
}

function DashboardStrip({ dashboard }: { dashboard: AdminDashboardResponse }) {
  const cards = [
    ["Employees", dashboard.employee_counts.total, Users],
    ["Active", dashboard.employee_counts.active, CheckCircle2],
    ["Suspended", dashboard.employee_counts.suspended, Ban],
    ["Departments", dashboard.department_count, Building2],
    ["Recently Active", dashboard.recently_active_employees, Activity],
    ["Open Complaints", dashboard.open_complaints, ShieldCheck],
  ] as const;
  return (
    <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(150px, 1fr))", gap: 12 }}>
      {cards.map(([label, value, Icon]) => <div className="stat-card" key={label}><Icon size={16} style={{ color: "var(--color-primary)" }} /><span style={{ fontSize: 24, fontWeight: 800 }}>{value.toLocaleString()}</span><span style={{ color: "var(--color-on-surface-variant)", fontSize: 12 }}>{label}</span></div>)}
    </div>
  );
}

function TabButton({ active, onClick, icon, label }: { active: boolean; onClick: () => void; icon: React.ReactNode; label: string }) {
  return <button className={`tab-item ${active ? "active" : ""}`} onClick={onClick}><span style={{ display: "flex", alignItems: "center", gap: 6 }}>{icon}{label}</span></button>;
}

function EmployeeModal({ employee, departments, employees, onClose, onSaved }: { employee: EmployeeRead | null; departments: DepartmentRead[]; employees: EmployeeRead[]; onClose: () => void; onSaved: () => void }) {
  const [form, setForm] = useState<EmployeeCreateRequest>({
    name: employee?.name ?? emptyEmployeeForm.name,
    email: employee?.email ?? emptyEmployeeForm.email,
    password: "",
    role: employee?.role ?? emptyEmployeeForm.role,
    department_id: employee?.department_id ?? null,
    reports_to: employee?.reports_to ?? null,
  });
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function save() {
    setSaving(true); setError(null);
    try {
      if (employee) {
        await updateEmployee(employee.employee_id, { name: form.name, email: form.email, role: form.role, department_id: form.department_id || null, reports_to: form.reports_to || null });
      } else {
        await createEmployee(form);
      }
      await onSaved();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to save employee");
    } finally { setSaving(false); }
  }

  return (
    <Modal title={employee ? `Edit ${employee.employee_id}` : "New Employee"} onClose={onClose} footer={<><button className="btn-secondary" onClick={onClose}>Cancel</button><button className="btn-primary" onClick={save} disabled={saving || !form.name || !form.email || (!employee && !form.password)}>{saving ? <Loader2 size={14} className="animate-spin" /> : <Plus size={14} />}Save</button></>}>
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))", gap: 12 }}>
        <Field label="Name"><input className="form-input" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} /></Field>
        <Field label="Email"><input className="form-input" type="email" value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} /></Field>
        {!employee && <Field label="Initial Password"><input className="form-input" type="password" value={form.password} onChange={(e) => setForm({ ...form, password: e.target.value })} /></Field>}
        <Field label="Role"><select className="form-select" value={form.role} onChange={(e) => setForm({ ...form, role: e.target.value as EmployeeRole })}>{roles.map((r) => <option key={r} value={r}>{humanize(r)}</option>)}</select></Field>
        <Field label="Department"><select className="form-select" value={form.department_id ?? ""} onChange={(e) => setForm({ ...form, department_id: e.target.value || null })}><option value="">Unassigned</option>{departments.map((d) => <option key={d.id} value={d.id}>{d.name}</option>)}</select></Field>
        <Field label="Reports To"><select className="form-select" value={form.reports_to ?? ""} onChange={(e) => setForm({ ...form, reports_to: e.target.value || null })}><option value="">No manager</option>{employees.filter((e) => e.id !== employee?.id).map((e) => <option key={e.id} value={e.id}>{e.name} ({e.employee_id})</option>)}</select></Field>
      </div>
      {error && <div className="alert-error" style={{ marginTop: 12 }}>{error}</div>}
    </Modal>
  );
}

function DepartmentsPanel({ departments, onChanged }: { departments: DepartmentRead[]; onChanged: () => void }) {
  const [name, setName] = useState("");
  const [code, setCode] = useState("");
  const [error, setError] = useState<string | null>(null);
  async function submit() {
    try { setError(null); await createDepartment({ name, code }); setName(""); setCode(""); await onChanged(); }
    catch (err) { setError(err instanceof Error ? err.message : "Failed to create department"); }
  }
  return <div className="card"><div className="card-header"><strong>Departments</strong><div style={{ display: "flex", gap: 8 }}><input className="form-input" placeholder="Name" value={name} onChange={(e) => setName(e.target.value)} /><input className="form-input" placeholder="Code" value={code} onChange={(e) => setCode(e.target.value)} /><button className="btn-primary" onClick={submit} disabled={!name || !code}><Plus size={14} />Add</button></div></div>{error && <div className="alert-error" style={{ margin: 16 }}>{error}</div>}<table className="data-table"><thead><tr><th>Name</th><th>Code</th><th>Employees</th><th>Created</th></tr></thead><tbody>{departments.map((d) => <tr key={d.id}><td>{d.name}</td><td><span className="id-pill">{d.code}</span></td><td>{d.employee_count}</td><td>{formatDateTime(d.created_at)}</td></tr>)}</tbody></table></div>;
}

function AuditPanel({ auditLogs, loginHistory }: { auditLogs: AuditLogEntry[]; loginHistory: LoginHistoryEntry[] }) {
  return <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(360px, 1fr))", gap: 16 }}><LogCard title="Recent Audit Logs" rows={auditLogs.map((l) => ({ id: l.id, primary: l.action, secondary: `${l.actor_name ?? l.actor_employee_id ?? "System"} -> ${l.target_type ?? "-"}`, time: l.created_at }))} /><LogCard title="Login History" rows={loginHistory.map((l) => ({ id: l.id, primary: l.action, secondary: l.actor_name ?? l.employee_id ?? String(l.details?.email ?? "Unknown"), time: l.created_at }))} /></div>;
}

function LogCard({ title, rows }: { title: string; rows: { id: string; primary: string; secondary: string; time: string }[] }) {
  return <div className="card"><div className="card-header"><strong>{title}</strong></div><table className="data-table"><thead><tr><th>Action</th><th>Actor/Target</th><th>Time</th></tr></thead><tbody>{rows.map((row) => <tr key={row.id}><td>{humanize(row.primary)}</td><td>{row.secondary}</td><td>{formatDateTime(row.time)}</td></tr>)}</tbody></table></div>;
}

function ReportsPanel() {
  async function run(kind: "employee" | "department") {
    const blob = kind === "employee" ? await downloadEmployeePerformanceReport() : await downloadDepartmentReport();
    triggerBlobDownload(blob, kind === "employee" ? "employee-performance.csv" : "department-report.csv");
  }
  return <div className="card"><div className="card-header"><strong>Admin CSV Reports</strong></div><div className="card-body" style={{ display: "flex", gap: 12, flexWrap: "wrap" }}><button className="btn-primary" onClick={() => run("employee")}><Download size={14} />Employee Performance</button><button className="btn-secondary" onClick={() => run("department")}><Download size={14} />Department Report</button></div></div>;
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return <label><span className="form-label">{label}</span>{children}</label>;
}

function roleVariant(role: string): BadgeVariant {
  if (role === "super_admin" || role === "admin") return "info";
  if (role === "manager") return "warning";
  return "neutral";
}

function statusVariant(status: string): BadgeVariant {
  if (status === "active") return "success";
  if (status === "suspended") return "danger";
  return "neutral";
}
