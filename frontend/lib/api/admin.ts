import { download, request } from "./client";
import type {
  AdminDashboardResponse,
  AuditLogListResponse,
  DepartmentCreateRequest,
  DepartmentListResponse,
  EmployeeCreateRequest,
  EmployeeListResponse,
  EmployeeRead,
  EmployeeUpdateRequest,
  LoginHistoryListResponse,
  ResetPasswordResponse,
} from "./types";

function query(params: object): string {
  const search = new URLSearchParams();
  Object.entries(params as Record<string, unknown>).forEach(([key, value]) => {
    if (value !== undefined && value !== null && value !== "") search.set(key, String(value));
  });
  const suffix = search.toString();
  return suffix ? `?${suffix}` : "";
}

export interface AdminListParams {
  limit?: number;
  offset?: number;
  search?: string;
  role?: string;
  status?: string;
  department_id?: string;
}

export function getAdminDashboard(): Promise<AdminDashboardResponse> {
  return request<AdminDashboardResponse>("/api/admin/dashboard");
}

export function listEmployees(params: AdminListParams = {}): Promise<EmployeeListResponse> {
  return request<EmployeeListResponse>(`/api/admin/employees${query(params)}`);
}

export function createEmployee(body: EmployeeCreateRequest): Promise<EmployeeRead> {
  return request<EmployeeRead>("/api/admin/employees", {
    method: "POST",
    body: JSON.stringify(body),
  });
}

export function updateEmployee(employeeId: string, body: EmployeeUpdateRequest): Promise<EmployeeRead> {
  return request<EmployeeRead>(`/api/admin/employees/${encodeURIComponent(employeeId)}`, {
    method: "PATCH",
    body: JSON.stringify(body),
  });
}

export function assignEmployee(employeeId: string, body: { department_id?: string | null; reports_to?: string | null }): Promise<EmployeeRead> {
  return request<EmployeeRead>(`/api/admin/employees/${encodeURIComponent(employeeId)}/assign`, {
    method: "POST",
    body: JSON.stringify(body),
  });
}

export function suspendEmployee(employeeId: string, reason: string): Promise<EmployeeRead> {
  return request<EmployeeRead>(`/api/admin/employees/${encodeURIComponent(employeeId)}/suspend`, {
    method: "POST",
    body: JSON.stringify({ reason }),
  });
}

export function activateEmployee(employeeId: string): Promise<EmployeeRead> {
  return request<EmployeeRead>(`/api/admin/employees/${encodeURIComponent(employeeId)}/activate`, { method: "POST" });
}

export function resetEmployeePassword(employeeId: string): Promise<ResetPasswordResponse> {
  return request<ResetPasswordResponse>(`/api/admin/employees/${encodeURIComponent(employeeId)}/reset-password`, { method: "POST" });
}

export function listDepartments(params: { limit?: number; offset?: number } = {}): Promise<DepartmentListResponse> {
  return request<DepartmentListResponse>(`/api/admin/departments${query(params)}`);
}

export function createDepartment(body: DepartmentCreateRequest) {
  return request("/api/admin/departments", {
    method: "POST",
    body: JSON.stringify(body),
  });
}

export function listAuditLogs(params: { limit?: number; offset?: number; action?: string } = {}): Promise<AuditLogListResponse> {
  return request<AuditLogListResponse>(`/api/admin/audit-logs${query(params)}`);
}

export function listLoginHistory(params: { limit?: number; offset?: number; success?: boolean | "" } = {}): Promise<LoginHistoryListResponse> {
  return request<LoginHistoryListResponse>(`/api/admin/login-history${query(params)}`);
}

export function downloadEmployeePerformanceReport(): Promise<Blob> {
  return download("/api/admin/reports/employee-performance.csv");
}

export function downloadDepartmentReport(): Promise<Blob> {
  return download("/api/admin/reports/department.csv");
}

