import { useAuth } from '@clerk/clerk-react'
import { useCallback } from 'react'

/**
 * Custom hook that provides a getToken() function backed by Clerk's session.
 * Returns a fresh JWT on each call — never stale, never from localStorage.
 *
 * Usage:
 *   const { getToken } = useAuthToken()
 *   const token = await getToken()
 *   const repos = await getRepos(token)
 */
export function useAuthToken() {
  const { getToken: clerkGetToken } = useAuth()

  const getToken = useCallback(async () => {
    try {
      const token = await clerkGetToken()
      return token
    } catch {
      return null
    }
  }, [clerkGetToken])

  return { getToken }
}
