import type { ActionFunctionArgs } from "@remix-run/node";
import { createApiProxy } from "~/services/api.server";

export async function action({ request }: ActionFunctionArgs) {
  if (request.method !== "POST") {
    return new Response("Method not allowed", { status: 405 });
  }

  try {
    const { proxy, headers } = await createApiProxy(request);
    const { message } = await request.json();

    if (!message || typeof message !== "string") {
      return new Response("Invalid message", {
        status: 400,
        headers
      });
    }

    return proxy.proxyStream("/api/v1/chat/message", {
      method: "POST",
      body: JSON.stringify({ message })
    });
  } catch (error) {
    if (error instanceof Response) {
      return error;
    }
    console.error("Chat stream route error:", error);
    return new Response("Internal server error", { status: 500 });
  }
}
