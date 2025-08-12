import type { ActionFunctionArgs, LoaderFunctionArgs } from "@remix-run/node";
import { signOut } from "~/services/auth.server";

export async function action({ request }: ActionFunctionArgs) {
  return signOut(request);
}

export async function loader({ request }: LoaderFunctionArgs) {
  return signOut(request);
}
