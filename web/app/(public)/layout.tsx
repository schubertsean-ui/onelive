import "./public.css";

export const metadata = {
  title: "1Live — Tonight in Austin",
  description:
    "Tonight's live music, art, food, and culture across Austin and the surrounding counties. Every event shows how well it's verified.",
  openGraph: {
    title: "1Live — Tonight in Austin",
    description:
      "Tonight's live music, art, food, and culture across Austin. Every event shows how well it's verified.",
    type: "website",
  },
};

export default function PublicLayout({ children }: { children: React.ReactNode }) {
  // The public surface intentionally does NOT use the ops `.container` chrome.
  return <div className="pub">{children}</div>;
}
