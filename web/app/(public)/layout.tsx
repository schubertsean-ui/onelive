import "./public.css";

export const metadata = {
  title: "1Live — What's on in Austin",
  description:
    "What's happening in Austin and the surrounding counties, by date. Pick Today, Tonight, a weekend, or a kind.",
  openGraph: {
    title: "1Live — What's on in Austin",
    description:
      "What's happening in Austin, by date. Pick Today, Tonight, a weekend, or a kind.",
    type: "website",
  },
};

export default function PublicLayout({ children }: { children: React.ReactNode }) {
  // The public surface intentionally does NOT use the ops `.container` chrome.
  return <div className="pub">{children}</div>;
}
