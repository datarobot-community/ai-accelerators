export interface IOAuthProvider {
  id: string;
  name: string;
  status?: string | null;
  type?: string;
  client_id?: string | null;
  metadata?: Record<string, unknown> | null;
}

export interface IOAuthProviderListResponse {
  providers: IOAuthProvider[];
}

export interface IOAuthAuthorizeResponse {
  redirect_url: string;
}

export interface OAuthAuthorizeCallback {
  isSuccess: boolean;
  isError: boolean;
  error: Record<string, unknown> | null;
}

export interface IOAuthIdentityValidation {
  provider_id: string;
  provider_type: string;
  is_valid: boolean;
  error_status_code: number | null;
}

export interface IValidateOAuthIdentitiesResponse {
  identities: IOAuthIdentityValidation[];
}
