import type { Metadata } from "next";
import { Space_Grotesk, JetBrains_Mono } from "next/font/google";
import "./globals.css";
import { ConfigureAmplify } from "./components/ConfigureAmplify";

const spaceGrotesk = Space_Grotesk({
  subsets: ["latin"],
  variable: "--font-space-grotesk",
});

const jetbrainsMono = JetBrains_Mono({
  subsets: ["latin"],
  variable: "--font-jetbrains-mono",
});

export const metadata: Metadata = {
  title: "Memory Architecture Tester",
  description: "Test and compare AWS memory services: AgentCore Memory, Bedrock KB, S3 Vectors",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="ja" className={`${spaceGrotesk.variable} ${jetbrainsMono.variable}`}>
      <body className="bg-slate-950 text-slate-100 min-h-screen">
        <ConfigureAmplify />
        {children}
      </body>
    </html>
  );
}




