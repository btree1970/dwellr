import { createServerClient, parse, serialize } from "@supabase/ssr";
import { redirect } from "@remix-run/node";

export function createSupabaseServerClient(request: Request) {
  const cookies = parse(request.headers.get("Cookie") ?? "");
  const headers = new Headers();

  const supabase = createServerClient(
    process.env.SUPABASE_URL!,
    process.env.SUPABASE_ANON_KEY!,
    {
      cookies: {
        get(name: string) {
          return cookies[name];
        },
        set(name: string, value: string, options: any) {
          headers.append("Set-Cookie", serialize(name, value, options));
        },
        remove(name: string, options: any) {
          headers.append("Set-Cookie", serialize(name, "", options));
        },
      },
    }
  );

  return { supabase, headers };
}

export async function getAuthenticatedUser(request: Request) {
  const { supabase, headers } = createSupabaseServerClient(request);

  const {
    data: { user },
  } = await supabase.auth.getUser();

  return { user, headers };
}

export async function requireAuthenticatedUser(request: Request) {
  const { user, headers } = await getAuthenticatedUser(request);

  if (!user) {
    throw redirect("/login", { headers });
  }

  return { user, headers };
}

export async function signIn(
  request: Request,
  email: string,
  password: string
) {
  const { supabase, headers } = createSupabaseServerClient(request);

  const { data, error } = await supabase.auth.signInWithPassword({
    email,
    password,
  });

  if (error) {
    return { error: error.message, headers };
  }

  return { user: data.user, headers };
}

export async function signUp(
  request: Request,
  email: string,
  password: string
) {
  const { supabase, headers } = createSupabaseServerClient(request);

  const { data, error } = await supabase.auth.signUp({
    email,
    password,
  });

  if (error) {
    return { error: error.message, headers };
  }

  return { user: data.user, headers };
}

export async function signOut(request: Request) {
  const { supabase, headers } = createSupabaseServerClient(request);

  await supabase.auth.signOut();

  return redirect("/", { headers });
}
