import { useState, useEffect, useMemo } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import { CheckCircle2, AlertCircle } from 'lucide-react';
import {
  useOauthProviders,
  useAuthorizeProvider,
  useValidateOAuthIdentities,
} from '@/api/oauth/hooks';
import { useCurrentUser } from '@/api/auth/hooks';
import { getBaseUrl } from '@/lib/utils.ts';
import { Button } from '@/components/ui/button';
import { PATHS } from '@/constants/path';
import { Skeleton } from '@/components/ui/skeleton';

export const SettingsSources = () => {
  const {
    data: providers = [],
    isLoading,
    isError: isErrorFetchingProviders,
  } = useOauthProviders();
  const { mutate: authorizeProvider, isPending } = useAuthorizeProvider();
  const [connectingId, setConnectingId] = useState<string | null>(null);
  const { data: currentUser } = useCurrentUser();
  const { mutate: validateOAuthIdentities } = useValidateOAuthIdentities();

  const connectedIds = useMemo(() => {
    if (currentUser?.identities) {
      return new Set(currentUser.identities.map(id => id.provider_id));
    }
  }, [currentUser?.identities]);

  let baseUrl = getBaseUrl();
  if (baseUrl.endsWith('/')) {
    baseUrl = baseUrl.slice(0, -1);
  }
  const redirectUri = `${window.location.origin}${baseUrl}${PATHS.OAUTH_CB}`;
  const location = useLocation();
  const navigate = useNavigate();
  const [oauthError, setOauthError] = useState<{ code: string; message?: string } | null>(null);

  useEffect(() => {
    const params = new URLSearchParams(location.search);
    const errorCode = params.get('error');
    const errorMessage = params.get('error_message');
    if (errorCode) {
      setOauthError({ code: errorCode, message: errorMessage || undefined });
      params.delete('error');
      params.delete('error_message');
      navigate({ pathname: location.pathname, search: params.toString() }, { replace: true });
    }
  }, [location, navigate]);

  // Validate OAuth tokens on mount, refetch user if any are invalid
  useEffect(() => {
    validateOAuthIdentities();
  }, [validateOAuthIdentities]);

  return (
    <div className="flex-1 p-8">
      <h2 className="text-xl font-semibold mb-6">Connected sources</h2>
      {oauthError && (
        <>
          <AlertCircle className="h-4 w-4" />
          <div>
            <p className="font-medium mb-1">Failed to connect to OAuth provider</p>
            {oauthError.message && oauthError.message !== 'OAuth connection failed' ? (
              <p className="text-sm">
                {typeof oauthError.message === 'string'
                  ? oauthError.message
                  : 'Please try again or contact support if the problem persists.'}
              </p>
            ) : (
              <p className="text-sm">
                Please try again or contact support if the problem persists.
              </p>
            )}
          </div>
        </>
      )}

      {isLoading && (
        <div className="space-y-4">
          <Skeleton key={0} className="h-20 w-full rounded-md" />
          <Skeleton key={1} className="h-20 w-full rounded-md" />
          <Skeleton key={2} className="h-20 w-full rounded-md" />
        </div>
      )}

      {isErrorFetchingProviders && (
        <p className="text-destructive">Failed to load connected sources.</p>
      )}

      {!isLoading && !isErrorFetchingProviders && providers.length === 0 && (
        <p className="text-muted-foreground">No sources available.</p>
      )}

      {!isLoading && providers.length > 0 && (
        <div className="divide-y divide-border">
          {providers.map(provider => (
            <div key={provider.id} className="flex items-center justify-between py-4">
              <div>
                <p className="font-medium">
                  {provider.type
                    ? provider.type.charAt(0).toUpperCase() + provider.type.slice(1)
                    : provider.name || provider.id}
                </p>
                {/* placeholder description */}
              </div>
              {connectedIds?.has(provider.id) ? (
                <span className="flex items-center gap-1 text-green-500 font-medium">
                  <CheckCircle2 className="w-4 h-4" /> Connected
                </span>
              ) : (
                <Button
                  variant="outline"
                  disabled={isPending && connectingId === provider.id}
                  onClick={() => {
                    setConnectingId(provider.id);
                    authorizeProvider(
                      {
                        providerId: provider.id,
                        redirect_uri: redirectUri,
                      },
                      {
                        onSuccess: ({ redirect_url }) => {
                          window.location.href = redirect_url;
                        },
                        onError: () => {
                          setConnectingId(null);
                        },
                      }
                    );
                  }}
                >
                  Connect
                </Button>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
};
