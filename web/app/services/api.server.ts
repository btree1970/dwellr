interface ApiRequestOptions {
  method?: string;
  headers?: Record<string, string>;
  body?: any;
}

class ApiClient {
  private baseUrl: string;

  constructor() {
    this.baseUrl = process.env.API_BASE_URL || "http://localhost:8000";
  }

  private async request<T>(
    path: string,
    accessToken: string | null,
    options: ApiRequestOptions = {}
  ): Promise<T> {
    const url = `${this.baseUrl}${path}`;

    const headers: Record<string, string> = {
      "Content-Type": "application/json",
      ...options.headers,
    };

    if (accessToken) {
      headers.Authorization = `Bearer ${accessToken}`;
    }

    const response = await fetch(url, {
      method: options.method || "GET",
      headers,
      body: options.body ? JSON.stringify(options.body) : undefined,
    });

    if (!response.ok) {
      const errorText = await response.text();
      throw new Error(`API request failed: ${response.status} - ${errorText}`);
    }

    return response.json();
  }

  async testAuth(accessToken: string) {
    return this.request<{ message: string; user: any }>(
      "/test-auth",
      accessToken
    );
  }

  async getHealth() {
    return this.request<{ status: string; database: string }>(
      "/health",
      null
    );
  }

  async sendChatMessage(accessToken: string, message: string) {
    return this.request(
      "/api/v1/chat/message",
      accessToken,
      {
        method: "POST",
        body: { message },
      }
    );
  }

  async getChatHistory(accessToken: string) {
    return this.request<{
      messages: Array<{
        role: string;
        content: string;
        tool_calls?: any;
        timestamp?: string;
      }>;
      session_id: string;
      total_messages: number;
    }>("/api/v1/chat/history", accessToken);
  }
}

export const apiClient = new ApiClient();
