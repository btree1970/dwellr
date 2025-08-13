import { Message } from "./Message";
import { StreamingMessage } from "./StreamingMessage";
import type { ChatMessage } from "~/services/api.client";

interface MessageListProps {
  messages: ChatMessage[];
  isStreaming: boolean;
}

export function MessageList({ messages, isStreaming }: MessageListProps) {
  if (messages.length === 0 && !isStreaming) {
    return (
      <div className="flex items-center justify-center h-full text-gray-500">
        <div className="text-center">
          <svg
            className="mx-auto h-12 w-12 text-gray-400 mb-4"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M8 10h.01M12 10h.01M16 10h.01M9 16H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-5l-5 5v-5z"
            />
          </svg>
          <p className="text-lg font-medium mb-2">Start a conversation</p>
          <p className="text-sm">
            Ask me about rental properties and I'll help you find the perfect
            place
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {messages.map((message, index) => {
        const isLastMessage = index === messages.length - 1;
        const isStreamingMessage = isLastMessage && isStreaming && message.role === "assistant";

        if (isStreamingMessage) {
          return (
            <StreamingMessage
              key={index}
              content={message.content}
              toolCalls={message.tool_calls}
            />
          );
        }

        return <Message key={index} message={message} />;
      })}
    </div>
  );
}
