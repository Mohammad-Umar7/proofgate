import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Code galaxy",
  description: "Every function in curl and every call between them. Invented functions float outside, connected to nothing.",
};

export default function Layout({ children }: { children: React.ReactNode }) {
  return children;
}
