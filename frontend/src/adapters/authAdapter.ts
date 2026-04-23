import { type AuthLoginResponse } from '../types/api'

const ACCESS_TOKEN_KEY = 'access_token'
const REFRESH_TOKEN_KEY = 'refresh_token'

export const AUTH_STATE_CHANGED_EVENT = 'travelhub:auth-state-changed'

function isBrowser(): boolean {
  return typeof window !== 'undefined'
}

export function getAccessToken(): string | null {
  if (!isBrowser()) {
    return null
  }
  return window.localStorage.getItem(ACCESS_TOKEN_KEY)
}

export function hasAccessToken(): boolean {
  return Boolean(getAccessToken())
}

export function getRefreshToken(): string | null {
  if (!isBrowser()) {
    return null
  }
  return window.localStorage.getItem(REFRESH_TOKEN_KEY)
}

export function setAuthTokens(payload: AuthLoginResponse): void {
  if (!isBrowser()) {
    return
  }

  window.localStorage.setItem(ACCESS_TOKEN_KEY, payload.access_token)
  if (payload.refresh_token) {
    window.localStorage.setItem(REFRESH_TOKEN_KEY, payload.refresh_token)
  }
}

export function clearAuthStorage(): void {
  if (!isBrowser()) {
    return
  }

  window.localStorage.removeItem(ACCESS_TOKEN_KEY)
  window.localStorage.removeItem(REFRESH_TOKEN_KEY)
}

export function dispatchAuthStateChanged(authenticated: boolean): void {
  if (!isBrowser()) {
    return
  }

  window.dispatchEvent(
    new CustomEvent<{ authenticated: boolean }>(AUTH_STATE_CHANGED_EVENT, {
      detail: { authenticated },
    }),
  )
}
