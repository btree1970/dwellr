export interface ChatMessage {
  role: "user" | "assistant";
  content: string;
  tool_calls?: Array<{
    tool_name: string;
    args: any;
  }>;
  timestamp?: string;
}

export interface StreamEvent {
  type: "text_start" | "text_chunk" | "tool_call" | "error" | "done";
  content?: string;
  tool_name?: string;
  error?: string;
}

export type StreamEventHandler = (event: StreamEvent) => void;

export class ChatAPIClient {
  private abortController: AbortController | null = null;

  async streamMessage(
    message: string,
    onEvent: StreamEventHandler
  ): Promise<void> {
    this.abortController = new AbortController();

    try {
      const response = await fetch("/api/chat/stream", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ message }),
        signal: this.abortController.signal,
      });

      if (!response.ok) {
        const errorText = await response.text();
        throw new Error(`Chat request failed: ${response.status} - ${errorText}`);
      }

      const reader = response.body?.getReader();
      if (!reader) {
        throw new Error("No response body");
      }

      const decoder = new TextDecoder();
      let buffer = "";

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split("\n");
        buffer = lines.pop() || "";

        for (const line of lines) {
          if (line.startsWith("data: ")) {
            try {
              const data = JSON.parse(line.slice(6));
              onEvent(data as StreamEvent);
            } catch (error) {
              console.error("Failed to parse SSE event:", error, line);
            }
          }
        }
      }

      if (buffer.trim() && buffer.startsWith("data: ")) {
        try {
          const data = JSON.parse(buffer.slice(6));
          onEvent(data as StreamEvent);
        } catch (error) {
          console.error("Failed to parse final SSE event:", error, buffer);
        }
      }
    } catch (error) {
      if (error instanceof Error && error.name === "AbortError") {
        console.log("Chat stream aborted");
      } else {
        console.error("Chat stream error:", error);
        onEvent({
          type: "error",
          error: error instanceof Error ? error.message : "Unknown error",
        });
      }
    } finally {
      this.abortController = null;
    }
  }

  abortStream(): void {
    if (this.abortController) {
      this.abortController.abort();
      this.abortController = null;
    }
  }

  async getChatHistory(): Promise<{
    messages: ChatMessage[];
    session_id: string;
    total_messages: number;
  }> {
    const response = await fetch("/api/chat/history", {
      headers: {
        "Content-Type": "application/json",
      },
    });

    if (!response.ok) {
      const errorText = await response.text();
      throw new Error(`Failed to fetch chat history: ${response.status} - ${errorText}`);
    }

    return response.json();
  }
}

export const chatAPIClient = new ChatAPIClient();
