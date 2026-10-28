import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "FixBench",
  description: "NVIDIA Nemotron fixing real curl CVEs on Nebius Token Factory, judged by curl's own test suite.",
};

export default function Layout({ children }: { children: React.ReactNode }) {
  return children;
}
