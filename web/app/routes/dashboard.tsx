import type { LoaderFunctionArgs } from "@remix-run/node";
import { json } from "@remix-run/node";
import { Link, useLoaderData } from "@remix-run/react";
import {
  requireAuthenticatedUser,
  createSupabaseServerClient,
} from "~/services/auth.server";
import { apiClient } from "~/services/api.server";

export async function loader({ request }: LoaderFunctionArgs) {
  const { user, headers } = await requireAuthenticatedUser(request);

  const { supabase } = createSupabaseServerClient(request);
  const {
    data: { session },
  } = await supabase.auth.getSession();

  let apiTestResult = null;
  let apiError = null;

  if (session?.access_token) {
    try {
      apiTestResult = await apiClient.testAuth(session.access_token);
    } catch (error) {
      apiError =
        error instanceof Error ? error.message : "Failed to connect to API";
    }
  }

  return json(
    {
      user,
      apiTestResult,
      apiError,
    },
    { headers }
  );
}

export default function Dashboard() {
  const { user, apiTestResult, apiError } = useLoaderData<typeof loader>();

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="bg-white shadow">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center py-6">
            <h1 className="text-2xl font-bold text-gray-900">Dashboard</h1>
            <div className="flex items-center space-x-4">
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

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="bg-white overflow-hidden shadow rounded-lg">
          <div className="px-4 py-5 sm:p-6">
            <h2 className="text-lg font-medium text-gray-900 mb-4">
              Authentication Status
            </h2>

            <div className="space-y-4">
              <div className="bg-green-50 border border-green-200 rounded-md p-4">
                <div className="flex">
                  <div className="flex-shrink-0">
                    <svg
                      className="h-5 w-5 text-green-400"
                      viewBox="0 0 20 20"
                      fill="currentColor"
                    >
                      <path
                        fillRule="evenodd"
                        d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z"
                        clipRule="evenodd"
                      />
                    </svg>
                  </div>
                  <div className="ml-3">
                    <h3 className="text-sm font-medium text-green-800">
                      Supabase Authentication
                    </h3>
                    <div className="mt-2 text-sm text-green-700">
                      <p>Successfully authenticated with Supabase</p>
                      <p className="mt-1">User ID: {user.id}</p>
                      <p>Email: {user.email}</p>
                    </div>
                  </div>
                </div>
              </div>

              {apiTestResult ? (
                <div className="bg-green-50 border border-green-200 rounded-md p-4">
                  <div className="flex">
                    <div className="flex-shrink-0">
                      <svg
                        className="h-5 w-5 text-green-400"
                        viewBox="0 0 20 20"
                        fill="currentColor"
                      >
                        <path
                          fillRule="evenodd"
                          d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z"
                          clipRule="evenodd"
                        />
                      </svg>
                    </div>
                    <div className="ml-3">
                      <h3 className="text-sm font-medium text-green-800">
                        FastAPI Backend Connection
                      </h3>
                      <div className="mt-2 text-sm text-green-700">
                        <p>{apiTestResult.message}</p>
                        {apiTestResult.user && (
                          <>
                            <p className="mt-1">
                              Backend User ID: {apiTestResult.user.id}
                            </p>
                            <p>Backend User Name: {apiTestResult.user.name}</p>
                          </>
                        )}
                      </div>
                    </div>
                  </div>
                </div>
              ) : apiError ? (
                <div className="bg-red-50 border border-red-200 rounded-md p-4">
                  <div className="flex">
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
                    <div className="ml-3">
                      <h3 className="text-sm font-medium text-red-800">
                        FastAPI Backend Connection Failed
                      </h3>
                      <div className="mt-2 text-sm text-red-700">
                        <p>{apiError}</p>
                        <p className="mt-1">
                          Make sure the backend is running on port 8000
                        </p>
                      </div>
                    </div>
                  </div>
                </div>
              ) : null}
            </div>

            <div className="mt-6 border-t pt-6">
              <h3 className="text-sm font-medium text-gray-900 mb-4">
                Quick Actions
              </h3>
              <div className="space-y-3">
                <Link
                  to="/chat"
                  className="block w-full text-center px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
                >
                  Start Chat with AI Assistant
                </Link>
              </div>
            </div>

            <div className="mt-6 border-t pt-6">
              <h3 className="text-sm font-medium text-gray-900 mb-2">
                System Status
              </h3>
              <ul className="list-disc list-inside text-sm text-gray-600 space-y-1">
                <li>SSR authentication is working</li>
                <li>User data fetched server-side before rendering</li>
                <li>Session stored in secure httpOnly cookies</li>
                <li>
                  FastAPI backend connection shows end-to-end integration
                </li>
              </ul>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
