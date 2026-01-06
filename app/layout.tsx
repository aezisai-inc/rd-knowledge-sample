"use client";

import { useState, useEffect } from "react";
import { Amplify } from "aws-amplify";
import "./globals.css";
import { Authenticator } from "@aws-amplify/ui-react";
import "@aws-amplify/ui-react/styles.css";
import outputs from "./amplify_outputs.json";

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const [isConfigured, setIsConfigured] = useState(false);

  useEffect(() => {
    try {
      Amplify.configure(outputs);
      setIsConfigured(true);
    } catch (error) {
      console.error("Amplify configuration failed:", error);
      setIsConfigured(true);
    }
  }, []);

  if (!isConfigured) {
    return (
      <html lang="ja">
        <body className="bg-slate-900 text-white min-h-screen flex items-center justify-center">
          <p className="text-slate-400">読み込み中...</p>
        </body>
      </html>
    );
  }

  return (
    <html lang="ja">
      <head>
        <title>Knowledge Sample</title>
      </head>
      <body className="bg-slate-900 text-white min-h-screen">
        <Authenticator hideSignUp={false}>
          {({ signOut, user }) => (
            <div className="min-h-screen">
              <header className="bg-slate-800 border-b border-slate-700 px-4 py-2 flex justify-between items-center">
                <span className="text-slate-300 text-sm">
                  {user?.signInDetails?.loginId || user?.username}
                </span>
                <button
                  onClick={signOut}
                  className="text-sm text-slate-400 hover:text-white"
                >
                  ログアウト
                </button>
              </header>
              <main>{children}</main>
            </div>
          )}
        </Authenticator>
      </body>
    </html>
  );
}
