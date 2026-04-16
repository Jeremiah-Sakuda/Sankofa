import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Narrative",
};

export default function NarrativeLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return children;
}
