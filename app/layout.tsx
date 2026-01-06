"use client";

import { useState, useEffect } from "react";
import { Amplify } from "aws-amplify";
import { Space_Grotesk, JetBrains_Mono } from "next/font/google";
import "./globals.css";
import { Authenticator } from "@aws-amplify/ui-react";
import "@aws-amplify/ui-react/styles.css";
import outputs from "./amplify_outputs.json";

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
  const [isConfigured, setIsConfigured] = useState(false);

  useEffect(() => {
    // Amplify設定を確実に1回だけ実行
    try {
      Amplify.configure(outputs);
      console.log("Amplify configured successfully");
      setIsConfigured(true);
    } catch (error) {
      console.error("Amplify configuration failed:", error);
      setIsConfigured(true); // エラーでも続行
    }
  }, []);

  // 設定完了まではローディング表示
  if (!isConfigured) {
    return (
      <html lang="ja" className={`${spaceGrotesk.variable} ${jetbrainsMono.variable}`}>
        <body className="bg-slate-950 text-slate-100 min-h-screen flex items-center justify-center">
          <div className="text-center">
            <div className="w-12 h-12 border-4 border-blue-500 border-t-transparent rounded-full animate-spin mx-auto mb-4" />
            <p className="text-slate-400">初期化中...</p>
          </div>
        </body>
      </html>
    );
  }

  return (
    <html lang="ja" className={`${spaceGrotesk.variable} ${jetbrainsMono.variable}`}>
      <head>
        <title>rd-knowledge-sample | AWS Nova Series 技術検証</title>
        <meta name="description" content="Test and compare AWS memory services: AgentCore Memory, Bedrock KB, S3 Vectors" />
      </head>
      <body className="bg-slate-950 text-slate-100 min-h-screen">
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




