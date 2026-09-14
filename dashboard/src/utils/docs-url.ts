import { DOCUMENTATION } from '@/constants/Project'

/**
 * BluePanel documentation currently lives with the project repository.
 * Keep every in-app documentation link inside the BluePanel project instead
 * of redirecting users to an upstream documentation host.
 */
export function getDocsUrl(_pagePath: string): string {
  return DOCUMENTATION
}
