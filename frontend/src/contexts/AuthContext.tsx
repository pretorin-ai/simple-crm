import { createContext, useContext, useState, useEffect, useCallback, ReactNode } from 'react';
import { useNavigate } from 'react-router-dom';
import { User, getCurrentUser, login as apiLogin, googleLogin as apiGoogleLogin, LoginCredentials, setAuthToken, clearAuthToken, getAuthToken, setRefreshToken } from '@/lib/api';

interface AuthContextType {
  user: User | null;
  isLoading: boolean;
  isAdmin: boolean;
  login: (credentials: LoginCredentials) => Promise<void>;
  loginWithGoogle: (credential: string) => Promise<void>;
  logout: () => void;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const navigate = useNavigate();

  const isAdmin = user?.role === 'admin';

  const logout = useCallback(() => {
    clearAuthToken();
    setUser(null);
    navigate('/login');
  }, [navigate]);

  useEffect(() => {
    // Check if user is already logged in
    const token = getAuthToken();
    if (token) {
      getCurrentUser()
        .then(setUser)
        .catch(() => {
          clearAuthToken();
        })
        .finally(() => setIsLoading(false));
    } else {
      setIsLoading(false);
    }
  }, []);

  // Listen for 401 unauthorized events from the API client
  useEffect(() => {
    const handleUnauthorized = () => {
      setUser(null);
      navigate('/login');
    };
    window.addEventListener('auth:unauthorized', handleUnauthorized);
    return () => window.removeEventListener('auth:unauthorized', handleUnauthorized);
  }, [navigate]);

  const login = async (credentials: LoginCredentials) => {
    const { access_token, refresh_token } = await apiLogin(credentials);
    setAuthToken(access_token);
    if (refresh_token) setRefreshToken(refresh_token);
    const userData = await getCurrentUser();
    setUser(userData);
  };

  const loginWithGoogle = async (credential: string) => {
    const { access_token, refresh_token } = await apiGoogleLogin(credential);
    setAuthToken(access_token);
    if (refresh_token) setRefreshToken(refresh_token);
    const userData = await getCurrentUser();
    setUser(userData);
  };

  return (
    <AuthContext.Provider value={{ user, isLoading, isAdmin, login, loginWithGoogle, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

// eslint-disable-next-line react-refresh/only-export-components
export function useAuth() {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
}
