import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import {
  getAuthToken,
  setAuthToken,
  clearAuthToken,
  getRefreshToken,
  setRefreshToken,
  login,
  getCurrentUser,
  getContacts,
  deleteContact,
} from './api';

// We need to test the internal fetchApi behavior via the exported functions that use it.

const MOCK_USER = {
  id: 'u1',
  email: 'test@example.com',
  name: 'Test User',
  role: 'user' as const,
  is_active: true,
  created_at: '2025-01-01T00:00:00Z',
  updated_at: '2025-01-01T00:00:00Z',
};

describe('auth token helpers', () => {
  beforeEach(() => {
    localStorage.clear();
  });

  it('getAuthToken returns null when no token set', () => {
    expect(getAuthToken()).toBeNull();
  });

  it('setAuthToken stores token, getAuthToken retrieves it', () => {
    setAuthToken('my-token');
    expect(getAuthToken()).toBe('my-token');
  });

  it('clearAuthToken removes token', () => {
    setAuthToken('my-token');
    clearAuthToken();
    expect(getAuthToken()).toBeNull();
  });
});

describe('fetchApi (via exported functions)', () => {
  let fetchSpy: ReturnType<typeof vi.fn>;

  beforeEach(() => {
    localStorage.clear();
    fetchSpy = vi.fn();
    vi.stubGlobal('fetch', fetchSpy);
  });

  afterEach(() => {
    vi.restoreAllMocks();
    vi.unstubAllGlobals();
  });

  it('sends Authorization header when token is set', async () => {
    setAuthToken('test-token');
    fetchSpy.mockResolvedValue({
      ok: true,
      status: 200,
      json: () => Promise.resolve(MOCK_USER),
    });

    await getCurrentUser();

    expect(fetchSpy).toHaveBeenCalledOnce();
    const [url, opts] = fetchSpy.mock.calls[0];
    expect(url).toContain('/auth/me');
    expect(opts.headers['Authorization']).toBe('Bearer test-token');
    expect(opts.headers['Content-Type']).toBe('application/json');
  });

  it('does not send Authorization header when no token', async () => {
    fetchSpy.mockResolvedValue({
      ok: true,
      status: 200,
      json: () => Promise.resolve(MOCK_USER),
    });

    await getCurrentUser();

    const [, opts] = fetchSpy.mock.calls[0];
    expect(opts.headers['Authorization']).toBeUndefined();
  });

  it('returns parsed JSON on success', async () => {
    fetchSpy.mockResolvedValue({
      ok: true,
      status: 200,
      json: () => Promise.resolve(MOCK_USER),
    });

    const result = await getCurrentUser();
    expect(result).toEqual(MOCK_USER);
  });

  it('returns undefined for 204 No Content', async () => {
    setAuthToken('test-token');
    fetchSpy.mockResolvedValue({
      ok: true,
      status: 204,
    });

    const result = await deleteContact('c1');
    expect(result).toBeUndefined();
  });

  it('clears token and dispatches auth:unauthorized on 401', async () => {
    setAuthToken('test-token');
    const eventHandler = vi.fn();
    window.addEventListener('auth:unauthorized', eventHandler);

    fetchSpy.mockResolvedValue({
      ok: false,
      status: 401,
      text: () => Promise.resolve(JSON.stringify({ detail: 'Not authenticated' })),
    });

    await expect(getCurrentUser()).rejects.toThrow('Not authenticated');
    expect(getAuthToken()).toBeNull();
    expect(eventHandler).toHaveBeenCalledOnce();

    window.removeEventListener('auth:unauthorized', eventHandler);
  });

  it('parses JSON error with string detail', async () => {
    fetchSpy.mockResolvedValue({
      ok: false,
      status: 400,
      text: () => Promise.resolve(JSON.stringify({ detail: 'Bad request data' })),
    });

    await expect(getCurrentUser()).rejects.toThrow('Bad request data');
  });

  it('parses JSON error with array detail (validation errors)', async () => {
    fetchSpy.mockResolvedValue({
      ok: false,
      status: 422,
      text: () =>
        Promise.resolve(
          JSON.stringify({
            detail: [
              { msg: 'field required', loc: ['body', 'email'] },
              { msg: 'invalid value', loc: ['body', 'name'] },
            ],
          })
        ),
    });

    await expect(getCurrentUser()).rejects.toThrow('field required, invalid value');
  });

  it('falls back to plain text error when response is not JSON', async () => {
    fetchSpy.mockResolvedValue({
      ok: false,
      status: 500,
      text: () => Promise.resolve('Internal Server Error'),
    });

    await expect(getCurrentUser()).rejects.toThrow('Internal Server Error');
  });

  it('falls back to status code message when body cannot be read', async () => {
    fetchSpy.mockResolvedValue({
      ok: false,
      status: 503,
      text: () => Promise.reject(new Error('cannot read body')),
    });

    await expect(getCurrentUser()).rejects.toThrow('Request failed (503)');
  });

  it('sends POST with JSON body for login', async () => {
    fetchSpy.mockResolvedValue({
      ok: true,
      status: 200,
      json: () => Promise.resolve({ access_token: 'tok123', token_type: 'bearer' }),
    });

    const result = await login({ email: 'test@example.com', password: 'pass' });

    expect(result).toEqual({ access_token: 'tok123', token_type: 'bearer' });
    const [, opts] = fetchSpy.mock.calls[0];
    expect(opts.method).toBe('POST');
    expect(JSON.parse(opts.body)).toEqual({ email: 'test@example.com', password: 'pass' });
  });

  it('passes an AbortSignal to fetch for timeout support', async () => {
    fetchSpy.mockResolvedValue({
      ok: true,
      status: 200,
      json: () => Promise.resolve(MOCK_USER),
    });

    await getCurrentUser();

    expect(fetchSpy).toHaveBeenCalledOnce();
    const [, opts] = fetchSpy.mock.calls[0];
    expect(opts.signal).toBeInstanceOf(AbortSignal);
  });
});

describe('token refresh', () => {
  let fetchSpy: ReturnType<typeof vi.fn>;

  beforeEach(() => {
    localStorage.clear();
    fetchSpy = vi.fn();
    vi.stubGlobal('fetch', fetchSpy);
  });

  afterEach(() => {
    vi.restoreAllMocks();
    vi.unstubAllGlobals();
  });

  it('refreshes the token on 401 for non-auth endpoints and retries', async () => {
    setAuthToken('expired-token');
    setRefreshToken('valid-refresh');

    const mockContacts = [{ id: 'c1', first_name: 'John' }];

    // First call: 401 (expired access token)
    // Second call: refresh endpoint succeeds
    // Third call: retry of original request succeeds
    fetchSpy
      .mockResolvedValueOnce({
        ok: false,
        status: 401,
        text: () => Promise.resolve(JSON.stringify({ detail: 'Token expired' })),
      })
      .mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: () => Promise.resolve({ access_token: 'new-access', refresh_token: 'new-refresh' }),
      })
      .mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: () => Promise.resolve(mockContacts),
      });

    const result = await getContacts();

    expect(result).toEqual(mockContacts);
    expect(fetchSpy).toHaveBeenCalledTimes(3);
    // Verify refresh endpoint was called
    expect(fetchSpy.mock.calls[1][0]).toContain('/auth/refresh');
    // Verify new tokens were stored
    expect(getAuthToken()).toBe('new-access');
    expect(getRefreshToken()).toBe('new-refresh');
  });

  it('does not attempt refresh for /auth/ endpoints', async () => {
    setAuthToken('expired-token');
    setRefreshToken('valid-refresh');

    const eventHandler = vi.fn();
    window.addEventListener('auth:unauthorized', eventHandler);

    fetchSpy.mockResolvedValueOnce({
      ok: false,
      status: 401,
      text: () => Promise.resolve(JSON.stringify({ detail: 'Not authenticated' })),
    });

    await expect(getCurrentUser()).rejects.toThrow('Not authenticated');
    // Only 1 call — no refresh attempted since getCurrentUser calls /auth/me
    expect(fetchSpy).toHaveBeenCalledTimes(1);
    expect(getAuthToken()).toBeNull();

    window.removeEventListener('auth:unauthorized', eventHandler);
  });

  it('falls back to logout when refresh fails', async () => {
    setAuthToken('expired-token');
    setRefreshToken('bad-refresh');

    const eventHandler = vi.fn();
    window.addEventListener('auth:unauthorized', eventHandler);

    // First call: 401 on non-auth endpoint
    // Second call: refresh endpoint also fails
    fetchSpy
      .mockResolvedValueOnce({
        ok: false,
        status: 401,
        text: () => Promise.resolve(JSON.stringify({ detail: 'Token expired' })),
      })
      .mockResolvedValueOnce({
        ok: false,
        status: 401,
        json: () => Promise.resolve({ detail: 'Invalid refresh token' }),
      });

    await expect(getContacts()).rejects.toThrow();
    expect(getAuthToken()).toBeNull();
    expect(eventHandler).toHaveBeenCalledOnce();

    window.removeEventListener('auth:unauthorized', eventHandler);
  });

  it('does not attempt refresh when no refresh token exists', async () => {
    setAuthToken('expired-token');
    // No refresh token set

    const eventHandler = vi.fn();
    window.addEventListener('auth:unauthorized', eventHandler);

    fetchSpy.mockResolvedValueOnce({
      ok: false,
      status: 401,
      text: () => Promise.resolve(JSON.stringify({ detail: 'Token expired' })),
    });

    await expect(getContacts()).rejects.toThrow();
    // 1 original call + 1 refresh attempt (which returns false immediately since no refresh token)
    expect(fetchSpy).toHaveBeenCalledTimes(1);
    expect(eventHandler).toHaveBeenCalledOnce();

    window.removeEventListener('auth:unauthorized', eventHandler);
  });

  it('deduplicates concurrent refresh attempts', async () => {
    setAuthToken('expired-token');
    setRefreshToken('valid-refresh');

    const mockContacts = [{ id: 'c1', first_name: 'John' }];

    // Both initial calls return 401
    // Then one refresh call succeeds
    // Then both retries succeed
    fetchSpy
      .mockResolvedValueOnce({
        ok: false,
        status: 401,
        text: () => Promise.resolve(JSON.stringify({ detail: 'Token expired' })),
      })
      .mockResolvedValueOnce({
        ok: false,
        status: 401,
        text: () => Promise.resolve(JSON.stringify({ detail: 'Token expired' })),
      })
      .mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: () => Promise.resolve({ access_token: 'new-access', refresh_token: 'new-refresh' }),
      })
      .mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: () => Promise.resolve(mockContacts),
      })
      .mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: () => Promise.resolve(mockContacts),
      });

    const [r1, r2] = await Promise.all([getContacts(), getContacts()]);

    expect(r1).toEqual(mockContacts);
    expect(r2).toEqual(mockContacts);
    // Should have only 1 refresh call despite 2 concurrent 401s
    const refreshCalls = fetchSpy.mock.calls.filter(
      (call: [string, ...unknown[]]) => call[0].includes('/auth/refresh')
    );
    expect(refreshCalls).toHaveLength(1);
  });

  it('refresh request includes AbortSignal for timeout', async () => {
    setAuthToken('expired-token');
    setRefreshToken('valid-refresh');

    const mockContacts = [{ id: 'c1', first_name: 'John' }];

    fetchSpy
      .mockResolvedValueOnce({
        ok: false,
        status: 401,
        text: () => Promise.resolve(JSON.stringify({ detail: 'Token expired' })),
      })
      .mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: () => Promise.resolve({ access_token: 'new-access', refresh_token: 'new-refresh' }),
      })
      .mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: () => Promise.resolve(mockContacts),
      });

    await getContacts();

    // Second call is the refresh — verify it has an AbortSignal
    const refreshCall = fetchSpy.mock.calls[1];
    expect(refreshCall[1].signal).toBeInstanceOf(AbortSignal);
  });
});
