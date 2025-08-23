import type { ActionFunctionArgs, LoaderFunctionArgs } from "@remix-run/node";
import { json, redirect } from "@remix-run/node";
import { Form, Link, useActionData, useSearchParams } from "@remix-run/react";
import { getAuthenticatedUser, signUp, signIn } from "~/services/auth.server";

export async function loader({ request }: LoaderFunctionArgs) {
  const { user } = await getAuthenticatedUser(request);

  if (user) {
    return redirect("/chat");
  }

  return json({});
}

export async function action({ request }: ActionFunctionArgs) {
  const formData = await request.formData();
  const email = formData.get("email") as string;
  const password = formData.get("password") as string;
  const confirmPassword = formData.get("confirmPassword") as string;

  if (!email || !password) {
    return json(
      { error: "Email and password are required" },
      { status: 400 }
    );
  }

  if (password !== confirmPassword) {
    return json(
      { error: "Passwords do not match" },
      { status: 400 }
    );
  }

  if (password.length < 6) {
    return json(
      { error: "Password must be at least 6 characters" },
      { status: 400 }
    );
  }

  const { user, error, headers } = await signUp(request, email, password);

  if (error) {
    return json(
      { error },
      { status: 400, headers }
    );
  }

  if (user) {
    // Auto sign in after signup
    const signInResult = await signIn(request, email, password);

    if (!signInResult.error && signInResult.user) {
      return redirect("/chat", { headers: signInResult.headers });
    }
  }

  return json(
    { success: true, message: "Account created! Please sign in." },
    { headers }
  );
}

export default function Signup() {
  const actionData = useActionData<typeof action>();
  const [searchParams] = useSearchParams();

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50 py-12 px-4 sm:px-6 lg:px-8">
      <div className="max-w-md w-full space-y-8">
        <div>
          <Link to="/" className="flex justify-center">
            <h1 className="text-3xl font-bold text-indigo-600">Dwell</h1>
          </Link>
          <h2 className="mt-6 text-center text-3xl font-extrabold text-gray-900">
            Create your account
          </h2>
          <p className="mt-2 text-center text-sm text-gray-600">
            Or{" "}
            <Link to="/login" className="font-medium text-indigo-600 hover:text-indigo-500">
              sign in to your existing account
            </Link>
          </p>
        </div>

        <Form method="post" className="mt-8 space-y-6">
          <div className="space-y-4">
            <div>
              <label htmlFor="email" className="block text-sm font-medium text-gray-700">
                Email address
              </label>
              <input
                id="email"
                name="email"
                type="email"
                autoComplete="email"
                required
                className="mt-1 appearance-none relative block w-full px-3 py-2 border border-gray-300 placeholder-gray-500 text-gray-900 rounded-md focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 focus:z-10 sm:text-sm"
                placeholder="you@example.com"
              />
            </div>
            <div>
              <label htmlFor="password" className="block text-sm font-medium text-gray-700">
                Password
              </label>
              <input
                id="password"
                name="password"
                type="password"
                autoComplete="new-password"
                required
                className="mt-1 appearance-none relative block w-full px-3 py-2 border border-gray-300 placeholder-gray-500 text-gray-900 rounded-md focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 focus:z-10 sm:text-sm"
                placeholder="At least 6 characters"
              />
            </div>
            <div>
              <label htmlFor="confirmPassword" className="block text-sm font-medium text-gray-700">
                Confirm Password
              </label>
              <input
                id="confirmPassword"
                name="confirmPassword"
                type="password"
                autoComplete="new-password"
                required
                className="mt-1 appearance-none relative block w-full px-3 py-2 border border-gray-300 placeholder-gray-500 text-gray-900 rounded-md focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 focus:z-10 sm:text-sm"
                placeholder="Re-enter your password"
              />
            </div>
          </div>

          {actionData && 'error' in actionData && (
            <div className="rounded-md bg-red-50 p-4">
              <div className="text-sm text-red-800">{actionData.error}</div>
            </div>
          )}

          {actionData && 'success' in actionData && (
            <div className="rounded-md bg-green-50 p-4">
              <div className="text-sm text-green-800">{actionData.message}</div>
            </div>
          )}

          <div>
            <button
              type="submit"
              className="group relative w-full flex justify-center py-2 px-4 border border-transparent text-sm font-medium rounded-md text-white bg-indigo-600 hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500"
            >
              Create Account
            </button>
          </div>

          <div className="text-center text-sm text-gray-500">
            By signing up, you agree to our{" "}
            <a href="#" className="text-indigo-600 hover:text-indigo-500">
              Terms of Service
            </a>{" "}
            and{" "}
            <a href="#" className="text-indigo-600 hover:text-indigo-500">
              Privacy Policy
            </a>
          </div>
        </Form>
      </div>
    </div>
  );
}
