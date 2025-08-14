import type { ActionFunctionArgs } from "@remix-run/node";
import { createSupabaseServerClient } from "~/services/auth.server";

export async function action({ request }: ActionFunctionArgs) {
  if (request.method !== "POST") {
    return new Response("Method not allowed", { status: 405 });
  }

  const { supabase, headers: authHeaders } = createSupabaseServerClient(request);

  const {
    data: { session },
  } = await supabase.auth.getSession();

  if (!session?.access_token) {
    return new Response("Unauthorized", {
      status: 401,
      headers: authHeaders
    });
  }

  const { message } = await request.json();

  if (!message || typeof message !== "string") {
    return new Response("Invalid message", {
      status: 400,
      headers: authHeaders
    });
  }

  const apiUrl = process.env.API_BASE_URL || "http://localhost:8000";

  try {
    const response = await fetch(`${apiUrl}/api/v1/chat/message`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${session.access_token}`,
      },
      body: JSON.stringify({ message }),
    });

    if (!response.ok) {
      const errorText = await response.text();
      return new Response(errorText, {
        status: response.status,
        headers: authHeaders
      });
    }

    const stream = new ReadableStream({
      async start(controller) {
        const reader = response.body?.getReader();
        if (!reader) {
          controller.close();
          return;
        }

        const decoder = new TextDecoder();
        let buffer = "";

        try {
          while (true) {
            const { done, value } = await reader.read();
            if (done) break;

            buffer += decoder.decode(value, { stream: true });
            const lines = buffer.split("\n");
            buffer = lines.pop() || "";

            for (const line of lines) {
              if (line.trim()) {
                controller.enqueue(new TextEncoder().encode(line + "\n"));
              }
            }
          }

          if (buffer.trim()) {
            controller.enqueue(new TextEncoder().encode(buffer + "\n"));
          }
        } catch (error) {
          console.error("Stream reading error:", error);
          controller.error(error);
        } finally {
          controller.close();
          reader.releaseLock();
        }
      },
    });

    return new Response(stream, {
      headers: {
        "Content-Type": "text/event-stream",
        "Cache-Control": "no-cache",
        "Connection": "keep-alive",
        ...Object.fromEntries(authHeaders.entries()),
      },
    });
  } catch (error) {
    console.error("Chat proxy error:", error);
    return new Response("Internal server error", {
      status: 500,
      headers: authHeaders
    });
  }
}
