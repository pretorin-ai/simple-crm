/**
 * OIDC/OAuth 2.0 utilities for Google OAuth authentication
 * Implements PKCE (Proof Key for Code Exchange) for secure authorization
 */

/**
 * Generate a cryptographically random string for PKCE
 */
function generateRandomString(length: number): string {
  const charset = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-._~';
  const randomValues = crypto.getRandomValues(new Uint8Array(length));
  return Array.from(randomValues)
    .map((v) => charset[v % charset.length])
    .join('');
}

/**
 * Generate SHA-256 hash of a string
 */
async function sha256(plain: string): Promise<ArrayBuffer> {
  const encoder = new TextEncoder();
  const data = encoder.encode(plain);
  return crypto.subtle.digest('SHA-256', data);
}

/**
 * Base64 URL encode an ArrayBuffer (RFC 4648)
 */
function base64UrlEncode(buffer: ArrayBuffer): string {
  const bytes = new Uint8Array(buffer);
  let binary = '';
  bytes.forEach((b) => (binary += String.fromCharCode(b)));
  return btoa(binary)
    .replace(/\+/g, '-')
    .replace(/\//g, '_')
    .replace(/=+$/, '');
}

/**
 * Generate PKCE code verifier and challenge
 *
 * The code verifier is a random string stored during auth initiation.
 * The code challenge is a SHA-256 hash of the verifier, sent to the IdP.
 * On callback, the verifier is sent to prove possession.
 */
export async function generatePKCE(): Promise<{ codeVerifier: string; codeChallenge: string }> {
  const codeVerifier = generateRandomString(64);
  const hashed = await sha256(codeVerifier);
  const codeChallenge = base64UrlEncode(hashed);
  return { codeVerifier, codeChallenge };
}

/**
 * Store PKCE code verifier in sessionStorage
 * sessionStorage is used because:
 * - It survives page redirects (unlike memory)
 * - It's isolated to the tab (more secure than localStorage)
 * - It's automatically cleared when tab closes
 */
export function storePKCEVerifier(verifier: string): void {
  sessionStorage.setItem('pkce_code_verifier', verifier);
}

/**
 * Retrieve stored PKCE code verifier
 */
export function getPKCEVerifier(): string | null {
  return sessionStorage.getItem('pkce_code_verifier');
}

/**
 * Clear stored PKCE code verifier
 */
export function clearPKCEVerifier(): void {
  sessionStorage.removeItem('pkce_code_verifier');
}

/**
 * OIDC configuration from backend
 */
export interface OIDCConfig {
  client_id: string;
  authorization_endpoint: string;
  redirect_uri: string;
  enabled: boolean;
}

/**
 * Build the authorization URL for Google OAuth
 * Includes PKCE code challenge and standard OIDC parameters
 */
export function buildAuthorizationUrl(
  config: OIDCConfig,
  codeChallenge: string,
  state?: string
): string {
  const params = new URLSearchParams({
    client_id: config.client_id,
    response_type: 'code',
    redirect_uri: config.redirect_uri,
    scope: 'openid email profile',
    code_challenge: codeChallenge,
    code_challenge_method: 'S256',
    // Google-specific: restrict to pretorin.com domain
    hd: 'pretorin.com',
  });

  if (state) {
    params.set('state', state);
  }

  return `${config.authorization_endpoint}?${params.toString()}`;
}
