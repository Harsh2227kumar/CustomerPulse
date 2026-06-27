import { request } from "./client";
import type { LoginRequest, LoginResponse, UserProfile } from "./types";

export function login(body: LoginRequest): Promise<LoginResponse> {
  return request<LoginResponse>("/api/auth/login", {
    method: "POST",
    body: JSON.stringify(body),
  });
}

export function getMe(): Promise<UserProfile> {
  return request<UserProfile>("/api/auth/me");
}
