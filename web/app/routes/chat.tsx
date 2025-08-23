import type { LoaderFunctionArgs } from "@remix-run/node";
import { json, redirect } from "@remix-run/node";
import { Link, useLoaderData, useNavigate } from "@remix-run/react";
import { useState, useEffect, useRef } from "react";
import { requireAuthenticatedUser } from "~/services/auth.server";
import { getUserProfile } from "~/services/profile.server";
import { MessageList } from "~/components/chat/MessageList";
import { MessageInput } from "~/components/chat/MessageInput";
import { useChat } from "~/hooks/useChat";

export async function loader({ request }: LoaderFunctionArgs) {
  const { user, headers } = await requireAuthenticatedUser(request);
  const profile = await getUserProfile(request);

  // If profile is already complete, redirect to dashboard
  if (profile?.profile_completed) {
    return redirect("/dashboard", { headers });
  }

  return json(
    {
      user,
      profile,
    },
    { headers }
  );
}

export default function Chat() {
  const { user, profile } = useLoaderData<typeof loader>();
  const navigate = useNavigate();
  const {
    messages,
    isStreaming,
    error,
    sendMessage,
    clearError,
    loadHistory,
  } = useChat();

  const [inputMessage, setInputMessage] = useState("");
  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    loadHistory();
  }, [loadHistory]);

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
              {profile && !profile.profile_completed && (
                <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-yellow-100 text-yellow-800">
                  Building Profile
                </span>
              )}
            </div>
            <div className="flex items-center space-x-4">
              {profile?.profile_completed && (
                <Link
                  to="/dashboard"
                  className="text-sm text-gray-600 hover:text-gray-900"
                >
                  Dashboard
                </Link>
              )}
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
        {/* Profile Progress Indicator */}
        {profile && !profile.profile_completed && profile.missing_requirements && profile.missing_requirements.length > 0 && (
          <div className="bg-blue-50 border-b border-blue-200 px-4 py-3">
            <div className="flex items-center">
              <svg className="h-5 w-5 text-blue-400 mr-2" fill="currentColor" viewBox="0 0 20 20">
                <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z" clipRule="evenodd" />
              </svg>
              <p className="text-sm text-blue-800">
                Tell me about your rental preferences to get personalized recommendations.
                {profile.missing_requirements.length > 0 && (
                  <span className="ml-1">
                    Missing: {profile.missing_requirements.join(", ")}
                  </span>
                )}
              </p>
            </div>
          </div>
        )}

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

        {/* Profile Completion Success Message */}
        {profile?.profile_completed && (
          <div className="bg-green-50 border-t border-green-200 px-4 py-3">
            <div className="flex items-center justify-between">
              <div className="flex items-center">
                <svg className="h-5 w-5 text-green-400 mr-2" fill="currentColor" viewBox="0 0 20 20">
                  <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
                </svg>
                <p className="text-sm text-green-800">
                  Profile complete! Ready to see your personalized listings.
                </p>
              </div>
              <Link
                to="/dashboard"
                className="text-sm font-medium text-green-600 hover:text-green-500"
              >
                Go to Dashboard →
              </Link>
            </div>
          </div>
        )}

        <div className="border-t bg-white px-4 py-4">
          <MessageInput
            value={inputMessage}
            onChange={setInputMessage}
            onSend={handleSendMessage}
            onKeyPress={handleKeyPress}
            disabled={isStreaming}
            placeholder={
              isStreaming
                ? "AI is responding..."
                : profile && !profile.profile_completed
                ? "Tell me about your ideal rental..."
                : "Ask about rental properties..."
            }
          />
        </div>
      </div>
    </div>
  );
}
