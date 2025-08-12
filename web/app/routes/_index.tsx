import type { MetaFunction, LoaderFunctionArgs } from "@remix-run/node";
import { json } from "@remix-run/node";
import { Link, useLoaderData } from "@remix-run/react";
import { getAuthenticatedUser } from "~/services/auth.server";

export const meta: MetaFunction = () => {
  return [
    { title: "Dwell - Home" },
    { name: "description", content: "Dwell Frontend with SSR Auth" },
  ];
};

export async function loader({ request }: LoaderFunctionArgs) {
  const { user } = await getAuthenticatedUser(request);
  return json({ user });
}

export default function Index() {
  const { user } = useLoaderData<typeof loader>();

  return (
    <div className="min-h-screen bg-gray-50 flex flex-col items-center justify-center py-12 px-4 sm:px-6 lg:px-8">
      <div className="max-w-md w-full space-y-8">
        <div className="text-center">
          <h1 className="text-4xl font-bold text-gray-900 mb-2">
            Dwell Frontend
          </h1>
          <p className="text-lg text-gray-600">
            SSR Auth Integration Demo
          </p>
        </div>

        <div className="bg-white shadow rounded-lg p-6">
          <div className="space-y-4">
            {user ? (
              <>
                <div className="text-center">
                  <p className="text-sm text-gray-600">Logged in as</p>
                  <p className="font-medium text-gray-900">{user.email}</p>
                </div>
                <div className="space-y-2">
                  <Link
                    to="/dashboard"
                    className="block w-full text-center py-2 px-4 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-indigo-600 hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500"
                  >
                    Go to Dashboard
                  </Link>
                  <Link
                    to="/logout"
                    className="block w-full text-center py-2 px-4 border border-gray-300 rounded-md shadow-sm text-sm font-medium text-gray-700 bg-white hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500"
                  >
                    Sign Out
                  </Link>
                </div>
              </>
            ) : (
              <>
                <p className="text-center text-gray-600">
                  Test the authentication flow
                </p>
                <div className="space-y-2">
                  <Link
                    to="/login"
                    className="block w-full text-center py-2 px-4 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-indigo-600 hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500"
                  >
                    Sign In
                  </Link>
                  <Link
                    to="/dashboard"
                    className="block w-full text-center py-2 px-4 border border-gray-300 rounded-md shadow-sm text-sm font-medium text-gray-700 bg-white hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500"
                  >
                    Try Protected Route
                  </Link>
                </div>
              </>
            )}
          </div>
        </div>

        <div className="bg-blue-50 border border-blue-200 rounded-md p-4">
          <h2 className="text-sm font-medium text-blue-900 mb-2">
            Architecture Overview
          </h2>
          <ul className="text-sm text-blue-700 space-y-1">
            <li>• Remix with SSR (Server-Side Rendering)</li>
            <li>• Supabase Auth with cookie-based sessions</li>
            <li>• FastAPI backend integration</li>
            <li>• TypeScript throughout</li>
          </ul>
        </div>
      </div>
    </div>
  );
}
