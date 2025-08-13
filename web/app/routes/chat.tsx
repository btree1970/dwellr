import type { LoaderFunctionArgs } from "@remix-run/node";
import { json } from "@remix-run/node";
import { Link, useLoaderData, useNavigate } from "@remix-run/react";
import { useState, useEffect, useRef } from "react";
import {
  requireAuthenticatedUser,
  createSupabaseServerClient,
} from "~/services/auth.server";
import { MessageList } from "~/components/chat/MessageList";
import { MessageInput } from "~/components/chat/MessageInput";
import { useChat } from "~/hooks/useChat";

export async function loader({ request }: LoaderFunctionArgs) {
  const { user, headers } = await requireAuthenticatedUser(request);

  const { supabase } = createSupabaseServerClient(request);
  const {
    data: { session },
  } = await supabase.auth.getSession();

  return json(
    {
      user,
      accessToken: session?.access_token || null,
    },
    { headers }
  );
}

export default function Chat() {
  const { user, accessToken } = useLoaderData<typeof loader>();
  const navigate = useNavigate();
  const {
    messages,
    isStreaming,
    error,
    sendMessage,
    clearError,
    loadHistory,
  } = useChat(accessToken);

  const [inputMessage, setInputMessage] = useState("");
  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!accessToken) {
      navigate("/login");
      return;
    }
    loadHistory();
  }, [accessToken, navigate, loadHistory]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const handleSendMessage = async () => {
    if (!inputMessage.trim() || isStreaming) return;

    const messageToSend = inputMessage;
    setInputMessage("");
    await sendMessage(messageToSend);
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSendMessage();
    }
  };

  return (
    <div className="flex flex-col h-screen bg-gray-50">
      <div className="bg-white shadow-sm border-b">
        <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center py-4">
            <div className="flex items-center space-x-4">
              <h1 className="text-xl font-semibold text-gray-900">
                Dwell AI Assistant
              </h1>
            </div>
            <div className="flex items-center space-x-4">
              <Link
                to="/dashboard"
                className="text-sm text-gray-600 hover:text-gray-900"
              >
                Dashboard
              </Link>
              <span className="text-sm text-gray-500">{user.email}</span>
              <Link
                to="/logout"
                className="text-sm text-red-600 hover:text-red-500"
              >
                Sign out
              </Link>
            </div>
          </div>
        </div>
      </div>

      <div className="flex-1 overflow-hidden flex flex-col max-w-6xl mx-auto w-full">
        <div className="flex-1 overflow-y-auto px-4 py-6">
          {error && (
            <div className="mb-4 p-4 bg-red-50 border border-red-200 rounded-lg">
              <div className="flex items-start">
                <div className="flex-shrink-0">
                  <svg
                    className="h-5 w-5 text-red-400"
                    viewBox="0 0 20 20"
                    fill="currentColor"
                  >
                    <path
                      fillRule="evenodd"
                      d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z"
                      clipRule="evenodd"
                    />
                  </svg>
                </div>
                <div className="ml-3 flex-1">
                  <p className="text-sm text-red-800">{error}</p>
                </div>
                <button
                  onClick={clearError}
                  className="ml-3 text-red-500 hover:text-red-600"
                >
                  <svg
                    className="h-5 w-5"
                    viewBox="0 0 20 20"
                    fill="currentColor"
                  >
                    <path
                      fillRule="evenodd"
                      d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z"
                      clipRule="evenodd"
                    />
                  </svg>
                </button>
              </div>
            </div>
          )}

          <MessageList messages={messages} isStreaming={isStreaming} />
          <div ref={messagesEndRef} />
        </div>

        <div className="border-t bg-white px-4 py-4">
          <MessageInput
            value={inputMessage}
            onChange={setInputMessage}
            onSend={handleSendMessage}
            onKeyPress={handleKeyPress}
            disabled={isStreaming || !accessToken}
            placeholder={
              isStreaming
                ? "AI is responding..."
                : "Ask about rental properties..."
            }
          />
        </div>
      </div>
    </div>
  );
}
