import { createApiProxy } from "~/services/api.server";

export interface UserProfile {
  id: string;
  name: string | null;
  occupation: string | null;
  bio: string | null;
  profile_completed: boolean;
  profile_completed_at: string | null;
  has_minimum_requirements: boolean;
  missing_requirements: string[];
  min_price: number | null;
  max_price: number | null;
  price_period: string | null;
  preferred_start_date: string | null;
  preferred_end_date: string | null;
  date_flexibility_days: number | null;
  preferred_listing_type: string | null;
  preference_profile: any;
  preference_version: number;
  last_preference_update: string | null;
  evaluation_credits: number;
  created_at: string;
  updated_at: string;
}

export async function getUserProfile(request: Request): Promise<UserProfile | null> {
  try {
    const { proxy } = await createApiProxy(request);
    const profile = await proxy.proxy<UserProfile>("/user/profile");
    return profile;
  } catch (error) {
    console.error("Failed to fetch user profile:", error);
    return null;
  }
}

export async function checkProfileCompletion(request: Request): Promise<{
  isComplete: boolean;
  profile: UserProfile | null;
}> {
  const profile = await getUserProfile(request);

  if (!profile) {
    return { isComplete: false, profile: null };
  }

  return {
    isComplete: profile.profile_completed,
    profile,
  };
}
