import { redirect } from "next/navigation";

/** Root redirect: / → /dashboard */
export default function RootPage() {
  redirect("/dashboard");
}
