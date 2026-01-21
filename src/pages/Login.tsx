import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { getOIDCConfig, OIDCConfig } from '@/lib/api';
import { generatePKCE, storePKCEVerifier, buildAuthorizationUrl } from '@/lib/oidc';
import { toast } from 'sonner';
import { useAuth } from '@/contexts/AuthContext';

export default function Login() {
  const [isLoading, setIsLoading] = useState(false);
  const [oidcConfig, setOidcConfig] = useState<OIDCConfig | null>(null);
  const [configError, setConfigError] = useState<string | null>(null);
  const { user } = useAuth();
  const navigate = useNavigate();

  // Redirect if already logged in
  useEffect(() => {
    if (user) {
      navigate('/dashboard', { replace: true });
    }
  }, [user, navigate]);

  // Fetch OIDC config on mount
  useEffect(() => {
    getOIDCConfig()
      .then((config) => {
        if (!config.enabled) {
          setConfigError('Single sign-on is not configured. Please contact your administrator.');
        } else {
          setOidcConfig(config);
        }
      })
      .catch(() => {
        setConfigError('Unable to connect to authentication service. Please try again later.');
      });
  }, []);

  const handleGoogleLogin = async () => {
    if (!oidcConfig?.enabled) return;

    setIsLoading(true);
    try {
      // Generate PKCE code verifier and challenge
      const { codeVerifier, codeChallenge } = await generatePKCE();

      // Store verifier in sessionStorage (survives redirect)
      storePKCEVerifier(codeVerifier);

      // Build authorization URL and redirect to Google
      const authUrl = buildAuthorizationUrl(oidcConfig, codeChallenge);
      window.location.href = authUrl;
    } catch (error) {
      toast.error('Failed to initiate sign-in. Please try again.');
      setIsLoading(false);
    }
  };

  return (
    <div className="flex min-h-screen items-center justify-center bg-background p-4">
      <Card className="w-full max-w-md">
        <CardHeader className="space-y-1 text-center">
          <CardTitle className="text-2xl font-bold">Pretorin CRM</CardTitle>
          <CardDescription>
            Sign in with your organization account
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          {configError ? (
            <div className="text-center text-sm text-muted-foreground p-4 bg-muted rounded-md">
              {configError}
            </div>
          ) : (
            <Button
              type="button"
              className="w-full"
              size="lg"
              onClick={handleGoogleLogin}
              disabled={isLoading || !oidcConfig?.enabled}
            >
              {isLoading ? (
                <>
                  <div className="h-4 w-4 mr-2 animate-spin rounded-full border-2 border-background border-t-transparent" />
                  Redirecting...
                </>
              ) : (
                'Sign in'
              )}
            </Button>
          )}
          <p className="text-xs text-center text-muted-foreground">
            Access is restricted to authorized organization members only.
          </p>
        </CardContent>
      </Card>
    </div>
  );
}
