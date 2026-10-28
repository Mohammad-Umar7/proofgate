import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "SlopBench",
  description: "ProofGate measured on 197 disclosed curl reports: every entry on curl's AI-slop list and every CVE that links its report.",
};

export default function Layout({ children }: { children: React.ReactNode }) {
  return children;
}
