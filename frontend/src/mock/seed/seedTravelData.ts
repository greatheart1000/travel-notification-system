import { TRAVEL_SEED_DATA, type TravelSeedStore } from './travelSeed'

const STORAGE_KEY = 'travel_hub_seed_v1'

function cloneSeed(): TravelSeedStore {
  return JSON.parse(JSON.stringify(TRAVEL_SEED_DATA)) as TravelSeedStore
}

function dedupeById<T extends { id: string }>(rows: T[]): T[] {
  const map = new Map<string, T>()
  rows.forEach((item) => map.set(item.id, item))
  return Array.from(map.values())
}

function dedupeByTeam<T extends { teamId: string }>(rows: T[]): T[] {
  const map = new Map<string, T>()
  rows.forEach((item) => map.set(JSON.stringify(item), item))
  return Array.from(map.values())
}

function normalizeStore(store: TravelSeedStore): TravelSeedStore {
  return {
    teams: dedupeById(store.teams),
    guests: dedupeById(store.guests),
    itineraryDays: dedupeById(store.itineraryDays),
    pickupPlans: dedupeById(store.pickupPlans),
    notificationTasks: dedupeById(store.notificationTasks),
    notificationConfigs: dedupeByTeam(store.notificationConfigs),
  }
}

export function seedTravelData(force = false): TravelSeedStore {
  if (typeof window === 'undefined') {
    return cloneSeed()
  }

  const seed = cloneSeed()
  const raw = window.localStorage.getItem(STORAGE_KEY)
  if (!raw || force) {
    const normalized = normalizeStore(seed)
    window.localStorage.setItem(STORAGE_KEY, JSON.stringify(normalized))
    return normalized
  }

  const parsed = JSON.parse(raw) as TravelSeedStore
  const merged = normalizeStore({
    teams: [...parsed.teams, ...seed.teams],
    guests: [...parsed.guests, ...seed.guests],
    itineraryDays: [...parsed.itineraryDays, ...seed.itineraryDays],
    pickupPlans: [...parsed.pickupPlans, ...seed.pickupPlans],
    notificationTasks: [...parsed.notificationTasks, ...seed.notificationTasks],
    notificationConfigs: [...parsed.notificationConfigs, ...seed.notificationConfigs],
  })

  window.localStorage.setItem(STORAGE_KEY, JSON.stringify(merged))
  return merged
}

export function readTravelSeedStore(): TravelSeedStore {
  return seedTravelData(false)
}

export function writeTravelSeedStore(store: TravelSeedStore): void {
  if (typeof window === 'undefined') return
  window.localStorage.setItem(STORAGE_KEY, JSON.stringify(normalizeStore(store)))
}
