import type { LoaderFunctionArgs } from "@remix-run/node";
import { json } from "@remix-run/node";
import { createSupabaseServerClient } from "~/services/auth.server";

export async function loader({ request }: LoaderFunctionArgs) {
  const { supabase, headers: authHeaders } = createSupabaseServerClient(request);

  const {
    data: { session },
  } = await supabase.auth.getSession();

  if (!session?.access_token) {
    return json(
      { error: "Unauthorized" },
      {
        status: 401,
        headers: authHeaders
      }
    );
  }

  const apiUrl = process.env.API_BASE_URL || "http://localhost:8000";

  try {
    const response = await fetch(`${apiUrl}/api/v1/chat/history`, {
      headers: {
        Authorization: `Bearer ${session.access_token}`,
      },
    });

    if (!response.ok) {
      const errorText = await response.text();
      return json(
        { error: errorText },
        {
          status: response.status,
          headers: authHeaders
        }
      );
    }

    const data = await response.json();
    return json(data, { headers: authHeaders });
  } catch (error) {
    console.error("Chat history proxy error:", error);
    return json(
      { error: "Internal server error" },
      {
        status: 500,
        headers: authHeaders
      }
    );
  }
}
