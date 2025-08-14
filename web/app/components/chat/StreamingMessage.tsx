import { useEffect, useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { Prism as SyntaxHighlighter } from "react-syntax-highlighter";
import { oneDark } from "react-syntax-highlighter/dist/cjs/styles/prism";
import type { Components } from "react-markdown";
import { ToolCallIndicator } from "./ToolCallIndicator";

interface StreamingMessageProps {
  content: string;
  toolCalls?: Array<{
    tool_name: string;
    args: any;
  }>;
}

export function StreamingMessage({ content, toolCalls }: StreamingMessageProps) {
  const [displayContent, setDisplayContent] = useState("");
  const [showCursor, setShowCursor] = useState(true);

  useEffect(() => {
    setDisplayContent(content);
  }, [content]);

  useEffect(() => {
    const interval = setInterval(() => {
      setShowCursor((prev) => !prev);
    }, 500);
    return () => clearInterval(interval);
  }, []);

  return (
    <div className="flex justify-start">
      <div className="max-w-3xl px-4 py-3 rounded-lg bg-white border border-gray-200 text-gray-900">
        {toolCalls && toolCalls.length > 0 && (
          <div className="mb-2">
            {toolCalls.map((toolCall, index) => (
              <ToolCallIndicator
                key={index}
                toolName={toolCall.tool_name}
                isDark={false}
              />
            ))}
          </div>
        )}

        <div className="prose prose-sm max-w-none">
          <ReactMarkdown
            remarkPlugins={[remarkGfm]}
            components={{
            code({ node, className, children, ...props }: any) {
              const inline = props.inline;
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
            p: ({ children }: any) => <p className="mb-2 last:mb-0">{children}</p>,
            ul: ({ children }: any) => (
              <ul className="list-disc list-inside mb-2">{children}</ul>
            ),
            ol: ({ children }: any) => (
              <ol className="list-decimal list-inside mb-2">{children}</ol>
            ),
            li: ({ children }: any) => <li className="mb-1">{children}</li>,
            a: ({ href, children }: any) => (
              <a
                href={href}
                target="_blank"
                rel="noopener noreferrer"
                className="text-blue-600 hover:text-blue-800 underline"
              >
                {children}
              </a>
            ),
            h1: ({ children }: any) => (
              <h1 className="text-xl font-bold mb-2">{children}</h1>
            ),
            h2: ({ children }: any) => (
              <h2 className="text-lg font-semibold mb-2">{children}</h2>
            ),
            h3: ({ children }: any) => (
              <h3 className="text-base font-semibold mb-2">{children}</h3>
            ),
            blockquote: ({ children }: any) => (
              <blockquote className="border-l-4 border-gray-300 pl-4 italic my-2">
                {children}
              </blockquote>
            ),
          }}
          >
            {displayContent}
          </ReactMarkdown>
        </div>
        {showCursor && (
          <span className="inline-block w-2 h-5 bg-gray-600 animate-pulse ml-1" />
        )}
      </div>
    </div>
  );
}
