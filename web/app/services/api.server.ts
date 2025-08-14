import { createSupabaseServerClient } from "~/services/auth.server";

interface ProxyOptions {
  timeout?: number;
  retries?: number;
  retryDelay?: number;
}

export class ApiProxy {
  private baseUrl: string;
  private request: Request;

  constructor(request: Request) {
    this.request = request;
    this.baseUrl = process.env.API_BASE_URL || "http://localhost:8000";
  }

  private async getAuthHeaders(): Promise<HeadersInit> {
    const { supabase } = createSupabaseServerClient(this.request);
    const {
      data: { session },
    } = await supabase.auth.getSession();

    if (!session?.access_token) {
      throw new Response("Unauthorized", { status: 401 });
    }

    return {
      Authorization: `Bearer ${session.access_token}`,
      "Content-Type": "application/json",
    };
  }

  private async fetchWithTimeout(
    url: string,
    init: RequestInit,
    timeout: number = 30000
  ): Promise<Response> {
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), timeout);

    try {
      const response = await fetch(url, {
        ...init,
        signal: controller.signal,
      });
      return response;
    } catch (error) {
      if (error instanceof Error && error.name === "AbortError") {
        throw new Error(`Request timeout after ${timeout}ms`);
      }
      throw error;
    } finally {
      clearTimeout(timeoutId);
    }
  }

  private async retryRequest(
    fn: () => Promise<Response>,
    retries: number,
    delay: number
  ): Promise<Response> {
    try {
      return await fn();
    } catch (error) {
      if (retries === 0) throw error;

      console.log(`Retrying request, ${retries} attempts remaining...`);
      await new Promise((resolve) => setTimeout(resolve, delay));
      return this.retryRequest(fn, retries - 1, delay * 2);
    }
  }

  private logRequest(
    method: string,
    path: string,
    startTime: number,
    status?: number,
    error?: Error
  ) {
    const duration = Date.now() - startTime;
    const logData = {
      timestamp: new Date().toISOString(),
      type: "api_proxy_request",
      method,
      path,
      duration,
      status,
      error: error?.message,
    };

    if (error) {
      console.error("API Proxy Error:", logData);
    } else {
      console.log("API Proxy Request:", logData);
    }
  }

  async proxy<T>(
    path: string,
    init?: RequestInit,
    options?: ProxyOptions
  ): Promise<T> {
    const startTime = Date.now();
    const method = init?.method || "GET";

    const defaultOptions: ProxyOptions = {
      timeout: 30000,
      retries: method === "GET" ? 3 : 0,
      retryDelay: 1000,
    };

    const opts = { ...defaultOptions, ...options };

    try {
      const authHeaders = await this.getAuthHeaders();
      const url = `${this.baseUrl}${path}`;

      const requestInit: RequestInit = {
        ...init,
        headers: {
          ...authHeaders,
          ...init?.headers,
        },
      };

      const makeRequest = () =>
        this.fetchWithTimeout(url, requestInit, opts.timeout);

      const response =
        opts.retries && opts.retries > 0
          ? await this.retryRequest(makeRequest, opts.retries, opts.retryDelay!)
          : await makeRequest();

      this.logRequest(method, path, startTime, response.status);

      if (!response.ok) {
        const errorText = await response.text();
        const error = new Error(
          `API request failed: ${response.status} - ${errorText}`
        );
        this.logRequest(method, path, startTime, response.status, error);
        throw new Response(errorText, {
          status: response.status,
          headers: response.headers,
        });
      }

      const data = await response.json();
      return data as T;
    } catch (error) {
      this.logRequest(method, path, startTime, undefined, error as Error);

      if (error instanceof Response) {
        throw error;
      }

      throw new Response(
        JSON.stringify({
          error:
            error instanceof Error ? error.message : "Internal server error",
        }),
        {
          status: 500,
          headers: { "Content-Type": "application/json" },
        }
      );
    }
  }

  async proxyStream(
    path: string,
    init?: RequestInit,
    options?: ProxyOptions
  ): Promise<Response> {
    const startTime = Date.now();
    const method = init?.method || "GET";

    const defaultOptions: ProxyOptions = {
      timeout: 60000,
      retries: 0,
      retryDelay: 1000,
    };

    const opts = { ...defaultOptions, ...options };

    try {
      const authHeaders = await this.getAuthHeaders();
      const url = `${this.baseUrl}${path}`;

      const requestInit: RequestInit = {
        ...init,
        headers: {
          ...authHeaders,
          ...init?.headers,
        },
      };

      const response = await this.fetchWithTimeout(
        url,
        requestInit,
        opts.timeout
      );

      this.logRequest(method, path, startTime, response.status);

      if (!response.ok) {
        const errorText = await response.text();
        const error = new Error(
          `Stream request failed: ${response.status} - ${errorText}`
        );
        this.logRequest(method, path, startTime, response.status, error);
        throw new Response(errorText, {
          status: response.status,
          headers: response.headers,
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
          Connection: "keep-alive",
        },
      });
    } catch (error) {
      this.logRequest(method, path, startTime, undefined, error as Error);

      if (error instanceof Response) {
        throw error;
      }

      throw new Response(
        JSON.stringify({
          error: error instanceof Error ? error.message : "Stream error",
        }),
        {
          status: 500,
          headers: { "Content-Type": "application/json" },
        }
      );
    }
  }
}

export async function createApiProxy(request: Request) {
  const { supabase, headers } = createSupabaseServerClient(request);
  const {
    data: { session },
  } = await supabase.auth.getSession();

  if (!session) {
    throw new Response("Unauthorized", { status: 401, headers });
  }

  return {
    proxy: new ApiProxy(request),
    headers,
  };
}
