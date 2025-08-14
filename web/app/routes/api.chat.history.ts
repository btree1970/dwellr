import type { LoaderFunctionArgs } from "@remix-run/node";
import { json } from "@remix-run/node";
import { createApiProxy } from "~/services/api.server";

export async function loader({ request }: LoaderFunctionArgs) {
  try {
    const { proxy, headers } = await createApiProxy(request);
    const data = await proxy.proxy("/api/v1/chat/history");

    return json(data, { headers });
  } catch (error) {
    if (error instanceof Response) {
      return error;
    }
    console.error("Chat history route error:", error);
    return json(
      { error: "Failed to load chat history" },
      { status: 500 }
    );
  }
}
