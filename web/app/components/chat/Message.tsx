import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { Prism as SyntaxHighlighter } from "react-syntax-highlighter";
import { oneDark } from "react-syntax-highlighter/dist/cjs/styles/prism";
import type { ChatMessage } from "~/services/api.client";
import { ToolCallIndicator } from "./ToolCallIndicator";

interface MessageProps {
  message: ChatMessage;
}

export function Message({ message }: MessageProps) {
  const isUser = message.role === "user";

  return (
    <div className={`flex ${isUser ? "justify-end" : "justify-start"}`}>
      <div
        className={`max-w-3xl px-4 py-3 rounded-lg ${
          isUser
            ? "bg-blue-600 text-white"
            : "bg-white border border-gray-200 text-gray-900"
        }`}
      >
        {message.tool_calls && message.tool_calls.length > 0 && (
          <div className="mb-2">
            {message.tool_calls.map((toolCall, index) => (
              <ToolCallIndicator
                key={index}
                toolName={toolCall.tool_name}
                isDark={isUser}
              />
            ))}
          </div>
        )}

        {isUser ? (
          <p className="whitespace-pre-wrap">{message.content}</p>
        ) : (
          <div className="prose prose-sm max-w-none">
            <ReactMarkdown
              remarkPlugins={[remarkGfm]}
              components={{
              code({ node, inline, className, children, ...props }) {
                const match = /language-(\w+)/.exec(className || "");
                return !inline && match ? (
                  <SyntaxHighlighter
                    style={oneDark}
                    language={match[1]}
                    PreTag="div"
                    className="rounded-md my-2"
                    {...props}
                  >
                    {String(children).replace(/\n$/, "")}
                  </SyntaxHighlighter>
                ) : (
                  <code
                    className="bg-gray-100 px-1 py-0.5 rounded text-sm font-mono"
                    {...props}
                  >
                    {children}
                  </code>
                );
              },
              p: ({ children }) => <p className="mb-2 last:mb-0">{children}</p>,
              ul: ({ children }) => (
                <ul className="list-disc list-inside mb-2">{children}</ul>
              ),
              ol: ({ children }) => (
                <ol className="list-decimal list-inside mb-2">{children}</ol>
              ),
              li: ({ children }) => <li className="mb-1">{children}</li>,
              a: ({ href, children }) => (
                <a
                  href={href}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-blue-600 hover:text-blue-800 underline"
                >
                  {children}
                </a>
              ),
              h1: ({ children }) => (
                <h1 className="text-xl font-bold mb-2">{children}</h1>
              ),
              h2: ({ children }) => (
                <h2 className="text-lg font-semibold mb-2">{children}</h2>
              ),
              h3: ({ children }) => (
                <h3 className="text-base font-semibold mb-2">{children}</h3>
              ),
              blockquote: ({ children }) => (
                <blockquote className="border-l-4 border-gray-300 pl-4 italic my-2">
                  {children}
                </blockquote>
              ),
            }}
            >
              {message.content}
            </ReactMarkdown>
          </div>
        )}
      </div>
    </div>
  );
}
