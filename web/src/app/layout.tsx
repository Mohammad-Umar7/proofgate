import type { Metadata, Viewport } from "next";
import { Inter, JetBrains_Mono } from "next/font/google";
import { Nav } from "@/components/Nav";
import "./globals.css";

const inter = Inter({ subsets: ["latin"], variable: "--font-inter", display: "swap" });
const mono = JetBrains_Mono({ subsets: ["latin"], variable: "--font-jetbrains", display: "swap" });

export const metadata: Metadata = {
  title: "ProofGate — prove a security report before a human reads it",
  description:
    "AI made fake security reports free to produce. ProofGate makes proving them cheap: every claim is checked against the real code, on NVIDIA Nemotron via Nebius Token Factory.",
};

export const viewport: Viewport = { themeColor: "#05060a" };

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className={`${inter.variable} ${mono.variable}`}>
      <body className="grain">
        <Nav />
        {children}
      </body>
    </html>
  );
}
