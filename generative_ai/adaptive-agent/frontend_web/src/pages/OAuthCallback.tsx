import { useEffect } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { useQueryClient } from '@tanstack/react-query';
import { useOauthCallback } from '@/api/oauth/hooks';
import { authKeys } from '@/api/auth/hooks';
import { oauthKeys } from '@/api/oauth/keys';
import { PATHS } from '@/constants/path';

const OAuthCallback = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const queryClient = useQueryClient();

  const buildErrorUrl = (errorCode: string, errorMessage?: string) => {
    const params = new URLSearchParams();
    params.set('error', errorCode);
    if (errorMessage) {
      params.set('error_message', errorMessage);
    }
    return `${PATHS.SETTINGS.SOURCES}?${params.toString()}`;
  };

  const params = new URLSearchParams(location.search);
  const providerError = params.get('error');

  useEffect(() => {
    // redirect to the page where we will show error, no need to send it to backend
    if (providerError) {
      navigate(buildErrorUrl(providerError), { replace: true });
    }
  }, [providerError, navigate]);

  const state = params.get('state');

  const { isSuccess, isError, error } = useOauthCallback(
    location.search,
    !!state && !providerError
  );

  useEffect(() => {
    if (isSuccess) {
      // Invalidate current user to refresh connected identities
      queryClient.invalidateQueries({ queryKey: authKeys.currentUser });
      // Invalidate OAuth providers in case connection state changed
      queryClient.invalidateQueries({ queryKey: oauthKeys.all });
      navigate(PATHS.SETTINGS.SOURCES, { replace: true });
    }
    if (isError) {
      // Just show the error message as a string
      let errorMessage = 'OAuth connection failed';
      if (error && typeof error === 'object' && 'response' in error) {
        const axiosError = error as { response?: { data?: { detail?: unknown } } };
        const detail = axiosError.response?.data?.detail;
        if (detail && typeof detail === 'object' && detail !== null && 'message' in detail) {
          errorMessage = String(detail.message);
        } else if (typeof detail === 'string') {
          errorMessage = detail;
        }
      }
      navigate(buildErrorUrl('oauth_failed', errorMessage), { replace: true });
    }
  }, [isSuccess, isError, navigate, queryClient, error]);

  return <div className="flex items-center justify-center h-full">Finishing sign-in…</div>;
};

export default OAuthCallback;
