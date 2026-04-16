import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Sample",
};

export default function SampleLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return children;
}
