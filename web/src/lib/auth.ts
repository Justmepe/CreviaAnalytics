const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export interface AuthUser {
  id: number;
  email: string;
  name: string | null;
  avatar_url: string | null;
  tier: string;
  subscription_status: string;
  created_at: string | null;
}

export interface AuthTokens {
  access_token: string;
  refresh_token: string;
  token_type: string;
}

const TOKEN_KEY = 'crevia_access_token';
const REFRESH_KEY = 'crevia_refresh_token';

export function getStoredToken(): string | null {
  if (typeof window === 'undefined') return null;
  return localStorage.getItem(TOKEN_KEY);
}

export function getStoredRefreshToken(): string | null {
  if (typeof window === 'undefined') return null;
  return localStorage.getItem(REFRESH_KEY);
}

export function storeTokens(tokens: AuthTokens): void {
  localStorage.setItem(TOKEN_KEY, tokens.access_token);
  localStorage.setItem(REFRESH_KEY, tokens.refresh_token);
}

export function clearTokens(): void {
  localStorage.removeItem(TOKEN_KEY);
  localStorage.removeItem(REFRESH_KEY);
}

async function authFetch<T>(endpoint: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${endpoint}`, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...options?.headers,
    },
  });

  if (!res.ok) {
    const body = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(body.detail || `HTTP ${res.status}`);
  }

  return res.json();
}

export async function register(email: string, password: string, name?: string): Promise<AuthTokens> {
  const tokens = await authFetch<AuthTokens>('/api/auth/register', {
    method: 'POST',
    body: JSON.stringify({ email, password, name }),
  });
  storeTokens(tokens);
  return tokens;
}

export async function login(email: string, password: string): Promise<AuthTokens> {
  const tokens = await authFetch<AuthTokens>('/api/auth/login', {
    method: 'POST',
    body: JSON.stringify({ email, password }),
  });
  storeTokens(tokens);
  return tokens;
}

export async function refreshAccessToken(): Promise<AuthTokens | null> {
  const refreshToken = getStoredRefreshToken();
  if (!refreshToken) return null;

  try {
    const tokens = await authFetch<AuthTokens>('/api/auth/refresh', {
      method: 'POST',
      body: JSON.stringify({ refresh_token: refreshToken }),
    });
    storeTokens(tokens);
    return tokens;
  } catch {
    clearTokens();
    return null;
  }
}

export async function fetchProfile(): Promise<AuthUser | null> {
  const token = getStoredToken();
  if (!token) return null;

  try {
    return await authFetch<AuthUser>('/api/auth/me', {
      headers: {
        Authorization: `Bearer ${token}`,
      },
    });
  } catch {
    // Token might be expired, try refresh
    const refreshed = await refreshAccessToken();
    if (refreshed) {
      return await authFetch<AuthUser>('/api/auth/me', {
        headers: {
          Authorization: `Bearer ${refreshed.access_token}`,
        },
      });
    }
    return null;
  }
}

export function logout(): void {
  clearTokens();
}
