import { useMutation, useQuery } from '@tanstack/react-query';
import {
  listProviders,
  authorizeProvider,
  getOAuthCallback,
  validateOAuthIdentities,
} from './requests';
import { oauthKeys } from './keys';
import {
  IOAuthProvider,
  IOAuthAuthorizeResponse,
  OAuthAuthorizeCallback,
  IValidateOAuthIdentitiesResponse,
} from './types';
import { authKeys } from '@/api/auth/hooks.ts';
import { queryClient } from '@/lib/query-client.ts';

export const useOauthProviders = () => {
  return useQuery<IOAuthProvider[], Error>({
    queryKey: oauthKeys.all,
    queryFn: () => listProviders(),
  });
};

export const useAuthorizeProvider = () => {
  return useMutation<IOAuthAuthorizeResponse, Error, { providerId: string; redirect_uri: string }>({
    mutationFn: ({ providerId, redirect_uri }) => authorizeProvider(providerId, { redirect_uri }),
  });
};

export const useOauthCallback = (query: string, enabled: boolean) => {
  return useQuery<OAuthAuthorizeCallback, Error>({
    queryKey: ['oauthCallback', query],
    queryFn: () => getOAuthCallback(query),
    enabled,
    retry: false,
  });
};

export const useValidateOAuthIdentities = () => {
  return useMutation<IValidateOAuthIdentitiesResponse, Error>({
    mutationFn: () => validateOAuthIdentities(),
    onSuccess: data => {
      if (data.identities.some(i => !i.is_valid)) {
        queryClient.invalidateQueries({ queryKey: authKeys.currentUser });
      }
    },
  });
};
