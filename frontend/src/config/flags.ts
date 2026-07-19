/**
 * Temporary admin gate until real auth lands.
 * Set VITE_IS_ADMIN=false in frontend/.env to hide admin-only nav.
 */
export function isAdmin(): boolean {
  const raw = import.meta.env.VITE_IS_ADMIN
  if (raw === undefined || raw === '') return true
  return raw === 'true' || raw === '1'
}
