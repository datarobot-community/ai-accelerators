export interface IIdentity {
  uuid: string;
  provider_id: string;
  provider_type: string;
  provider_user_id: string;
  provider_identity_id?: string | null;
}

export interface IUser {
  uuid: string;
  email: string;
  first_name: string;
  last_name: string;
  profile_image_url?: string | null;
  identities: IIdentity[];
}
