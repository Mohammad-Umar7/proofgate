import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Triage console",
  description: "Watch a real vulnerability report get proven or disproven, claim by claim, in nine stages on NVIDIA Nemotron.",
};

export default function Layout({ children }: { children: React.ReactNode }) {
  return children;
}
