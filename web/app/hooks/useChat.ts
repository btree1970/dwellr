import { useState, useCallback, useRef } from "react";
import { chatAPIClient, type ChatMessage, type StreamEvent } from "~/services/api.client";

export function useChat(accessToken: string | null) {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [isStreaming, setIsStreaming] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const currentStreamingMessage = useRef<string>("");
  const currentToolCalls = useRef<Array<{ tool_name: string; args: any }>>([]);

  const loadHistory = useCallback(async () => {
    if (!accessToken) return;

    try {
      const history = await chatAPIClient.getChatHistory(accessToken);
      setMessages(history.messages);
    } catch (err) {
      console.error("Failed to load chat history:", err);
      setError("Failed to load chat history");
    }
  }, [accessToken]);

  const handleStreamEvent = useCallback((event: StreamEvent) => {
    switch (event.type) {
      case "text_start":
        currentStreamingMessage.current = event.content || "";
        setMessages((prev) => {
          const newMessages = [...prev];
          const lastMessage = newMessages[newMessages.length - 1];

          if (lastMessage && lastMessage.role === "assistant" && !lastMessage.content) {
            lastMessage.content = currentStreamingMessage.current;
          } else {
            newMessages.push({
              role: "assistant",
              content: currentStreamingMessage.current,
              tool_calls: currentToolCalls.current.length > 0 ? [...currentToolCalls.current] : undefined,
            });
          }
          return newMessages;
        });
        break;

      case "text_chunk":
        currentStreamingMessage.current += event.content || "";
        setMessages((prev) => {
          const newMessages = [...prev];
          const lastMessage = newMessages[newMessages.length - 1];
          if (lastMessage && lastMessage.role === "assistant") {
            lastMessage.content = currentStreamingMessage.current;
          }
          return newMessages;
        });
        break;

      case "tool_call":
        if (event.tool_name) {
          const toolCall = { tool_name: event.tool_name, args: {} };
          currentToolCalls.current.push(toolCall);

          setMessages((prev) => {
            const newMessages = [...prev];
            const lastMessage = newMessages[newMessages.length - 1];

            if (lastMessage && lastMessage.role === "assistant") {
              lastMessage.tool_calls = [...currentToolCalls.current];
            } else {
              newMessages.push({
                role: "assistant",
                content: "",
                tool_calls: [...currentToolCalls.current],
              });
            }
            return newMessages;
          });
        }
        break;

      case "error":
        setError(event.error || "An error occurred");
        setIsStreaming(false);
        break;

      case "done":
        setIsStreaming(false);
        currentStreamingMessage.current = "";
        currentToolCalls.current = [];
        break;
    }
  }, []);

  const sendMessage = useCallback(async (message: string) => {
    if (!accessToken) {
      setError("Not authenticated");
      return;
    }

    setError(null);
    setIsStreaming(true);
    currentStreamingMessage.current = "";
    currentToolCalls.current = [];

    setMessages((prev) => [...prev, { role: "user", content: message }]);

    try {
      await chatAPIClient.streamMessage(accessToken, message, handleStreamEvent);
    } catch (err) {
      console.error("Failed to send message:", err);
      setError(err instanceof Error ? err.message : "Failed to send message");
      setIsStreaming(false);
    }
  }, [accessToken, handleStreamEvent]);

  const clearError = useCallback(() => {
    setError(null);
  }, []);

  const abortStream = useCallback(() => {
    chatAPIClient.abortStream();
    setIsStreaming(false);
  }, []);

  return {
    messages,
    isStreaming,
    error,
    sendMessage,
    clearError,
    loadHistory,
    abortStream,
  };
}
