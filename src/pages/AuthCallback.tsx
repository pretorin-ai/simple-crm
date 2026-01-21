import { useEffect, useState, useRef } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { oidcCallback } from '@/lib/api';
import { getPKCEVerifier, clearPKCEVerifier } from '@/lib/oidc';
import { useAuth } from '@/contexts/AuthContext';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { toast } from 'sonner';

/**
 * OAuth callback page that handles the redirect from Google.
 * Exchanges the authorization code for tokens and completes the login flow.
 */
export default function AuthCallback() {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const { setUserFromToken } = useAuth();
  const [error, setError] = useState<string | null>(null);
  const [isProcessing, setIsProcessing] = useState(true);
  const callbackProcessed = useRef(false);

  useEffect(() => {
    const handleCallback = async () => {
      // Prevent double execution
      if (callbackProcessed.current) {
        return;
      }
      callbackProcessed.current = true;
      // Check for error from identity provider
      const errorParam = searchParams.get('error');
      const errorDescription = searchParams.get('error_description');

      if (errorParam) {
        setError(errorDescription || `Authentication error: ${errorParam}`);
        setIsProcessing(false);
        return;
      }

      // Get authorization code
      const code = searchParams.get('code');
      if (!code) {
        setError('No authorization code received from identity provider.');
        setIsProcessing(false);
        return;
      }

      // Get stored PKCE verifier
      const codeVerifier = getPKCEVerifier();
      if (!codeVerifier) {
        setError('Session expired. Please try signing in again.');
        setIsProcessing(false);
        return;
      }

      try {
        // Exchange code for tokens
        const response = await oidcCallback({
          code,
          code_verifier: codeVerifier,
        });

        // Clear PKCE verifier
        clearPKCEVerifier();

        // Store the token and update auth state
        await setUserFromToken(response.access_token);

        // Show success message
        toast.success(`Welcome, ${response.user.name}!`);

        // Redirect to dashboard
        navigate('/dashboard', { replace: true });
      } catch (err) {
        // Clear PKCE verifier on error too
        clearPKCEVerifier();

        const message = err instanceof Error ? err.message : 'Authentication failed';
        setError(message);
        setIsProcessing(false);
      }
    };

    handleCallback();
  }, [searchParams, navigate, setUserFromToken]);

  if (error) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-background p-4">
        <Card className="w-full max-w-md">
          <CardHeader>
            <CardTitle className="text-destructive">Authentication Error</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <p className="text-muted-foreground">{error}</p>
            <Button
              variant="outline"
              className="w-full"
              onClick={() => navigate('/login', { replace: true })}
            >
              Return to Login
            </Button>
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-background p-4">
      <Card className="w-full max-w-md">
        <CardHeader>
          <CardTitle>Signing you in...</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex items-center space-x-2">
            <div className="h-4 w-4 animate-spin rounded-full border-2 border-primary border-t-transparent" />
            <p className="text-muted-foreground">Please wait while we complete authentication.</p>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
