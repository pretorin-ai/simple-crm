import { createContext, useContext, useState, useEffect, useCallback, ReactNode } from 'react';
import { User, getCurrentUser, setAuthToken, clearAuthToken, getAuthToken, getQueueCounts, QueueCounts } from '@/lib/api';

interface AuthContextType {
  user: User | null;
  isLoading: boolean;
  isAdmin: boolean;
  queueCounts: QueueCounts | null;
  setUserFromToken: (token: string) => Promise<void>;
  logout: () => void;
  refreshQueueCounts: () => Promise<void>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [queueCounts, setQueueCounts] = useState<QueueCounts | null>(null);

  const isAdmin = user?.role === 'admin';

  const refreshQueueCounts = useCallback(async () => {
    if (!getAuthToken()) return;
    try {
      const counts = await getQueueCounts();
      setQueueCounts(counts);
    } catch (error) {
      console.error('Failed to fetch queue counts:', error);
    }
  }, []);

  useEffect(() => {
    // Check if user is already logged in
    const token = getAuthToken();
    if (token) {
      getCurrentUser()
        .then((userData) => {
          setUser(userData);
          // Fetch initial queue counts
          refreshQueueCounts();
        })
        .catch(() => {
          clearAuthToken();
        })
        .finally(() => setIsLoading(false));
    } else {
      setIsLoading(false);
    }
  }, [refreshQueueCounts]);

  // Poll queue counts every 60 seconds when user is logged in
  useEffect(() => {
    if (!user) return;

    const interval = setInterval(() => {
      refreshQueueCounts();
    }, 60000);

    return () => clearInterval(interval);
  }, [user, refreshQueueCounts]);

  // Called by AuthCallback after successful OIDC authentication
  const setUserFromToken = async (token: string) => {
    setAuthToken(token);
    const userData = await getCurrentUser();
    setUser(userData);
    // Fetch queue counts after login
    refreshQueueCounts();
  };

  const logout = () => {
    // Clear local auth state and redirect to login
    clearAuthToken();
    setUser(null);
    setQueueCounts(null);
    window.location.href = '/login';
  };

  return (
    <AuthContext.Provider value={{ user, isLoading, isAdmin, queueCounts, setUserFromToken, logout, refreshQueueCounts }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
}
