import type { LoaderFunctionArgs } from "@remix-run/node";
import { json, redirect } from "@remix-run/node";
import { Link, useLoaderData } from "@remix-run/react";
import { requireAuthenticatedUser } from "~/services/auth.server";
import { getUserProfile } from "~/services/profile.server";

export async function loader({ request }: LoaderFunctionArgs) {
  const { user, headers } = await requireAuthenticatedUser(request);
  const profile = await getUserProfile(request);

  // If profile is not complete, redirect to chat
  if (!profile?.profile_completed) {
    return redirect("/chat", { headers });
  }

  return json(
    {
      user,
      profile,
    },
    { headers }
  );
}

export default function Dashboard() {
  const { user, profile } = useLoaderData<typeof loader>();

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Navigation */}
      <div className="bg-white shadow">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center py-4">
            <div className="flex items-center space-x-8">
              <Link to="/" className="text-2xl font-bold text-indigo-600">
                Dwell
              </Link>
              <nav className="flex space-x-4">
                <Link
                  to="/dashboard"
                  className="text-gray-900 hover:text-gray-700 px-3 py-2 rounded-md text-sm font-medium"
                >
                  Dashboard
                </Link>
                <Link
                  to="/chat"
                  className="text-gray-500 hover:text-gray-700 px-3 py-2 rounded-md text-sm font-medium"
                >
                  AI Chat
                </Link>
              </nav>
            </div>
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
        <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
          {/* User Profile Card */}
          <div className="lg:col-span-1">
            <div className="bg-white overflow-hidden shadow rounded-lg">
              <div className="px-4 py-5 sm:p-6">
                <h3 className="text-lg font-medium text-gray-900 mb-4">
                  Your Profile
                </h3>
                <div className="space-y-3">
                  <div>
                    <p className="text-sm font-medium text-gray-500">Name</p>
                    <p className="mt-1 text-sm text-gray-900">
                      {profile?.name || "Not set"}
                    </p>
                  </div>
                  <div>
                    <p className="text-sm font-medium text-gray-500">Email</p>
                    <p className="mt-1 text-sm text-gray-900">{user.email}</p>
                  </div>
                  <div>
                    <p className="text-sm font-medium text-gray-500">
                      Price Range
                    </p>
                    <p className="mt-1 text-sm text-gray-900">
                      {profile?.min_price && profile?.max_price
                        ? `$${profile.min_price} - $${profile.max_price}${
                            profile.price_period
                              ? ` per ${profile.price_period}`
                              : ""
                          }`
                        : "Not set"}
                    </p>
                  </div>
                  <div>
                    <p className="text-sm font-medium text-gray-500">
                      Move-in Date
                    </p>
                    <p className="mt-1 text-sm text-gray-900">
                      {profile?.preferred_start_date
                        ? new Date(
                            profile.preferred_start_date
                          ).toLocaleDateString()
                        : "Flexible"}
                    </p>
                  </div>
                  <div className="pt-3 border-t">
                    <Link
                      to="/chat"
                      className="text-sm font-medium text-indigo-600 hover:text-indigo-500"
                    >
                      Update preferences →
                    </Link>
                  </div>
                </div>
              </div>
            </div>

            {/* Quick Stats */}
            <div className="mt-6 bg-white overflow-hidden shadow rounded-lg">
              <div className="px-4 py-5 sm:p-6">
                <h3 className="text-lg font-medium text-gray-900 mb-4">
                  Quick Stats
                </h3>
                <dl className="grid grid-cols-1 gap-4">
                  <div>
                    <dt className="text-sm font-medium text-gray-500">
                      Profile Status
                    </dt>
                    <dd className="mt-1 flex items-center">
                      <span className="px-2 py-1 text-xs font-medium bg-green-100 text-green-800 rounded-full">
                        Complete
                      </span>
                    </dd>
                  </div>
                  <div>
                    <dt className="text-sm font-medium text-gray-500">
                      Evaluation Credits
                    </dt>
                    <dd className="mt-1 text-2xl font-semibold text-gray-900">
                      {profile?.evaluation_credits || 0}
                    </dd>
                  </div>
                  <div>
                    <dt className="text-sm font-medium text-gray-500">
                      Member Since
                    </dt>
                    <dd className="mt-1 text-sm text-gray-900">
                      {profile?.created_at
                        ? new Date(profile.created_at).toLocaleDateString()
                        : "Today"}
                    </dd>
                  </div>
                </dl>
              </div>
            </div>
          </div>

          {/* Main Content - Listings */}
          <div className="lg:col-span-2">
            <div className="bg-white overflow-hidden shadow rounded-lg">
              <div className="px-4 py-5 sm:p-6">
                <div className="flex items-center justify-between mb-6">
                  <h2 className="text-lg font-medium text-gray-900">
                    Recommended Listings
                  </h2>
                  <button className="text-sm font-medium text-indigo-600 hover:text-indigo-500">
                    Filter
                  </button>
                </div>

                {/* Empty State */}
                <div className="text-center py-12">
                  <svg
                    className="mx-auto h-12 w-12 text-gray-400"
                    fill="none"
                    viewBox="0 0 24 24"
                    stroke="currentColor"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={2}
                      d="M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-5m-9 0H3m2 0h5M9 7h1m-1 4h1m4-4h1m-1 4h1m-5 10v-5a1 1 0 011-1h2a1 1 0 011 1v5m-4 0h4"
                    />
                  </svg>
                  <h3 className="mt-2 text-sm font-medium text-gray-900">
                    No listings yet
                  </h3>
                  <p className="mt-1 text-sm text-gray-500">
                    We're working on finding the perfect matches for you.
                  </p>
                  <p className="mt-1 text-sm text-gray-500">
                    New listings will appear here as they become available.
                  </p>
                  <div className="mt-6">
                    <Link
                      to="/chat"
                      className="inline-flex items-center px-4 py-2 border border-transparent shadow-sm text-sm font-medium rounded-md text-white bg-indigo-600 hover:bg-indigo-700"
                    >
                      <svg
                        className="-ml-1 mr-2 h-5 w-5"
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
                      Refine Preferences
                    </Link>
                  </div>
                </div>
              </div>
            </div>

            {/* Coming Soon Features */}
            <div className="mt-6 bg-blue-50 rounded-lg p-6">
              <h3 className="text-sm font-medium text-blue-900 mb-2">
                Coming Soon
              </h3>
              <ul className="text-sm text-blue-700 space-y-1">
                <li>• AI-scored listings based on your preferences</li>
                <li>• Real-time notifications for new matches</li>
                <li>• Save and compare your favorite properties</li>
              </ul>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
