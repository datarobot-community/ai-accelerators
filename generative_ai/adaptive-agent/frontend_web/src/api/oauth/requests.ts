import apiClient from '../apiClient';
import {
  IOAuthProvider,
  IOAuthProviderListResponse,
  IOAuthAuthorizeResponse,
  OAuthAuthorizeCallback,
  IValidateOAuthIdentitiesResponse,
} from './types';

/**
 * Fetches a list of OAuth providers available on the backend.
 */
export async function listProviders(signal?: AbortSignal): Promise<IOAuthProvider[]> {
  const { data } = await apiClient.get<IOAuthProviderListResponse>(`/v1/oauth/`, {
    signal,
  });

  return data.providers;
}

interface AuthorizeOptions {
  redirect_uri: string;
}

/**
 * Initiates the OAuth authorization flow for the given provider.
 * The backend returns the URL to redirect the user to. We then navigate the browser there.
 */
export async function authorizeProvider(
  providerId: string,
  options: AuthorizeOptions
): Promise<IOAuthAuthorizeResponse> {
  const { data } = await apiClient.post<IOAuthAuthorizeResponse>(`/v1/oauth/authorize/`, null, {
    params: {
      provider_id: providerId,
      redirect_uri: options.redirect_uri,
    },
  });

  return data;
}

export const getOAuthCallback = async (query: string): Promise<OAuthAuthorizeCallback> =>
  await apiClient.get(`/v1/oauth/callback/${query}`);

/**
 * Validates OAuth tokens by forcing a refresh.
 * Backend will delete identities that have been revoked.
 */
export async function validateOAuthIdentities(): Promise<IValidateOAuthIdentitiesResponse> {
  const { data } = await apiClient.post<IValidateOAuthIdentitiesResponse>(`/v1/oauth/validate/`);
  return data;
}
