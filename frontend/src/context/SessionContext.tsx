import { createContext, useContext, type ReactNode } from 'react'
import type { CurrentUser } from '../types/api'
import type { TenantInfo } from '../services/commercialApi'

export interface SessionValue {
  user: CurrentUser | null
  tenant: TenantInfo | null
  refreshSession: () => Promise<void>
}

const SessionContext = createContext<SessionValue>({
  user: null,
  tenant: null,
  refreshSession: async () => undefined,
})

export function SessionProvider({
  value,
  children,
}: {
  value: SessionValue
  children: ReactNode
}) {
  return <SessionContext.Provider value={value}>{children}</SessionContext.Provider>
}

export function useSession(): SessionValue {
  return useContext(SessionContext)
}
