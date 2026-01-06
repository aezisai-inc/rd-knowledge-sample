"use client";

import { Space_Grotesk, JetBrains_Mono } from "next/font/google";
import "./globals.css";
import { ConfigureAmplify } from "./components/ConfigureAmplify";
import { Authenticator } from "@aws-amplify/ui-react";
import "@aws-amplify/ui-react/styles.css";

const spaceGrotesk = Space_Grotesk({
  subsets: ["latin"],
  variable: "--font-space-grotesk",
});

const jetbrainsMono = JetBrains_Mono({
  subsets: ["latin"],
  variable: "--font-jetbrains-mono",
});

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="ja" className={`${spaceGrotesk.variable} ${jetbrainsMono.variable}`}>
      <head>
        <title>rd-knowledge-sample | AWS Nova Series 技術検証</title>
        <meta name="description" content="Test and compare AWS memory services: AgentCore Memory, Bedrock KB, S3 Vectors" />
      </head>
      <body className="bg-slate-950 text-slate-100 min-h-screen">
        <ConfigureAmplify />
        <Authenticator
          hideSignUp={false}
          components={{
            Header() {
              return (
                <div className="text-center py-6">
                  <h1 className="text-2xl font-bold text-white">🔐 ログイン</h1>
                  <p className="text-slate-400 text-sm mt-2">AWS Nova Series 技術検証</p>
                </div>
              );
            },
          }}
        >
          {({ signOut, user }) => (
            <div className="min-h-screen">
              <header className="bg-slate-900 border-b border-slate-800 px-4 py-2 flex justify-between items-center">
                <span className="text-sm text-slate-400">
                  👤 {user?.signInDetails?.loginId || user?.username}
                </span>
                <button
                  onClick={signOut}
                  className="text-sm bg-red-600 hover:bg-red-700 px-3 py-1 rounded"
                >
                  ログアウト
                </button>
              </header>
              {children}
            </div>
          )}
        </Authenticator>
      </body>
    </html>
  );
}




