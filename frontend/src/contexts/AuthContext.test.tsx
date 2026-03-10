import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, waitFor, act } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { AuthProvider, useAuth } from './AuthContext';

// Mock the api module
vi.mock('@/lib/api', () => ({
  getAuthToken: vi.fn(),
  setAuthToken: vi.fn(),
  clearAuthToken: vi.fn(),
  login: vi.fn(),
  googleLogin: vi.fn(),
  getCurrentUser: vi.fn(),
}));

import * as api from '@/lib/api';

const MOCK_USER = {
  id: 'u1',
  email: 'test@example.com',
  name: 'Test User',
  role: 'user' as const,
  is_active: true,
  created_at: '2025-01-01T00:00:00Z',
  updated_at: '2025-01-01T00:00:00Z',
};

// Test component that exposes auth context
function AuthConsumer() {
  const { user, isLoading, isAdmin, login, logout } = useAuth();

  return (
    <div>
      <div data-testid="loading">{String(isLoading)}</div>
      <div data-testid="user">{user ? user.name : 'null'}</div>
      <div data-testid="isAdmin">{String(isAdmin)}</div>
      <button onClick={() => login({ email: 'test@example.com', password: 'pass' })}>
        Login
      </button>
      <button onClick={logout}>Logout</button>
    </div>
  );
}

function renderWithAuth(initialEntries: string[] = ['/']) {
  return render(
    <MemoryRouter initialEntries={initialEntries}>
      <AuthProvider>
        <AuthConsumer />
      </AuthProvider>
    </MemoryRouter>
  );
}

describe('AuthContext', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('useAuth throws when used outside AuthProvider', () => {
    // Suppress console.error for the expected React error
    const spy = vi.spyOn(console, 'error').mockImplementation(() => {});
    expect(() => render(<AuthConsumer />)).toThrow('useAuth must be used within an AuthProvider');
    spy.mockRestore();
  });

  it('starts loading then resolves with no user when no token exists', async () => {
    vi.mocked(api.getAuthToken).mockReturnValue(null);

    renderWithAuth();

    // Should finish loading quickly with no user
    await waitFor(() => {
      expect(screen.getByTestId('loading').textContent).toBe('false');
    });
    expect(screen.getByTestId('user').textContent).toBe('null');
  });

  it('fetches user on mount when token exists', async () => {
    vi.mocked(api.getAuthToken).mockReturnValue('existing-token');
    vi.mocked(api.getCurrentUser).mockResolvedValue(MOCK_USER);

    renderWithAuth();

    await waitFor(() => {
      expect(screen.getByTestId('loading').textContent).toBe('false');
    });
    expect(screen.getByTestId('user').textContent).toBe('Test User');
    expect(api.getCurrentUser).toHaveBeenCalledOnce();
  });

  it('clears token when getCurrentUser fails on mount', async () => {
    vi.mocked(api.getAuthToken).mockReturnValue('expired-token');
    vi.mocked(api.getCurrentUser).mockRejectedValue(new Error('Unauthorized'));

    renderWithAuth();

    await waitFor(() => {
      expect(screen.getByTestId('loading').textContent).toBe('false');
    });
    expect(screen.getByTestId('user').textContent).toBe('null');
    expect(api.clearAuthToken).toHaveBeenCalled();
  });

  it('login stores token and fetches user', async () => {
    vi.mocked(api.getAuthToken).mockReturnValue(null);
    vi.mocked(api.login).mockResolvedValue({
      access_token: 'new-token',
      token_type: 'bearer',
    });
    vi.mocked(api.getCurrentUser).mockResolvedValue(MOCK_USER);

    renderWithAuth();

    // Wait for initial load
    await waitFor(() => {
      expect(screen.getByTestId('loading').textContent).toBe('false');
    });

    // Click login
    await act(async () => {
      screen.getByText('Login').click();
    });

    await waitFor(() => {
      expect(screen.getByTestId('user').textContent).toBe('Test User');
    });

    expect(api.login).toHaveBeenCalledWith({ email: 'test@example.com', password: 'pass' });
    expect(api.setAuthToken).toHaveBeenCalledWith('new-token');
    expect(api.getCurrentUser).toHaveBeenCalled();
  });

  it('logout clears token and user', async () => {
    vi.mocked(api.getAuthToken).mockReturnValue('existing-token');
    vi.mocked(api.getCurrentUser).mockResolvedValue(MOCK_USER);

    renderWithAuth();

    await waitFor(() => {
      expect(screen.getByTestId('user').textContent).toBe('Test User');
    });

    // Click logout
    await act(async () => {
      screen.getByText('Logout').click();
    });

    expect(api.clearAuthToken).toHaveBeenCalled();
    expect(screen.getByTestId('user').textContent).toBe('null');
  });

  it('auth:unauthorized event triggers logout (clears user and navigates)', async () => {
    vi.mocked(api.getAuthToken).mockReturnValue('existing-token');
    vi.mocked(api.getCurrentUser).mockResolvedValue(MOCK_USER);

    renderWithAuth();

    await waitFor(() => {
      expect(screen.getByTestId('user').textContent).toBe('Test User');
    });

    // Simulate the unauthorized event the API client dispatches
    await act(async () => {
      window.dispatchEvent(new Event('auth:unauthorized'));
    });

    expect(screen.getByTestId('user').textContent).toBe('null');
  });

  it('isAdmin is true for admin users', async () => {
    vi.mocked(api.getAuthToken).mockReturnValue('admin-token');
    vi.mocked(api.getCurrentUser).mockResolvedValue({ ...MOCK_USER, role: 'admin' });

    renderWithAuth();

    await waitFor(() => {
      expect(screen.getByTestId('isAdmin').textContent).toBe('true');
    });
  });

  it('isAdmin is false for regular users', async () => {
    vi.mocked(api.getAuthToken).mockReturnValue('user-token');
    vi.mocked(api.getCurrentUser).mockResolvedValue(MOCK_USER);

    renderWithAuth();

    await waitFor(() => {
      expect(screen.getByTestId('loading').textContent).toBe('false');
    });
    expect(screen.getByTestId('isAdmin').textContent).toBe('false');
  });
});
