import { redirect } from "next/navigation";

// Root sends visitors to the public "tonight" feed.
export default function RootPage() {
  redirect("/tonight");
}
