import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Adversarial arena",
  description: "A red-team agent writes ever more convincing fake reports; ProofGate has to catch every one with evidence.",
};

export default function Layout({ children }: { children: React.ReactNode }) {
  return children;
}
