"use client";

import { useState, useEffect } from "react";
import { Amplify } from "aws-amplify";
import { Space_Grotesk, JetBrains_Mono } from "next/font/google";
import "./globals.css";
import { Authenticator, ThemeProvider, Theme } from "@aws-amplify/ui-react";
import "@aws-amplify/ui-react/styles.css";
import outputs from "./amplify_outputs.json";

// ライトテーマ：白背景 + ダークテキスト
const lightTheme: Theme = {
  name: 'light-high-contrast',
  tokens: {
    colors: {
      background: {
        primary: { value: '#ffffff' },
        secondary: { value: '#f8fafc' },
      },
      font: {
        primary: { value: '#1e293b' },
        secondary: { value: '#475569' },
        interactive: { value: '#2563eb' },
      },
      brand: {
        primary: {
          10: { value: '#eff6ff' },
          20: { value: '#dbeafe' },
          40: { value: '#93c5fd' },
          60: { value: '#3b82f6' },
          80: { value: '#2563eb' },
          90: { value: '#1d4ed8' },
          100: { value: '#1e40af' },
        },
      },
      border: {
        primary: { value: '#cbd5e1' },
        secondary: { value: '#e2e8f0' },
      },
    },
    components: {
      authenticator: {
        router: {
          backgroundColor: { value: '#ffffff' },
          borderColor: { value: '#e2e8f0' },
        },
      },
      button: {
        primary: {
          backgroundColor: { value: '#2563eb' },
          color: { value: '#ffffff' },
          _hover: {
            backgroundColor: { value: '#1d4ed8' },
          },
        },
      },
      fieldcontrol: {
        backgroundColor: { value: '#ffffff' },
        borderColor: { value: '#cbd5e1' },
        color: { value: '#1e293b' },
        _focus: {
          borderColor: { value: '#3b82f6' },
        },
      },
      tabs: {
        item: {
          color: { value: '#64748b' },
          _active: {
            color: { value: '#2563eb' },
            borderColor: { value: '#2563eb' },
          },
          _hover: {
            color: { value: '#1e293b' },
          },
        },
      },
    },
    radii: {
      small: { value: '6px' },
      medium: { value: '8px' },
      large: { value: '12px' },
    },
    space: {
      small: { value: '0.75rem' },
      medium: { value: '1rem' },
      large: { value: '1.5rem' },
    },
  },
};

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
        <body className="bg-slate-100 text-slate-800 min-h-screen flex items-center justify-center">
          <div className="text-center">
            <div className="w-12 h-12 border-4 border-blue-600 border-t-transparent rounded-full animate-spin mx-auto mb-4" />
            <p className="text-slate-600">初期化中...</p>
          </div>
        </body>
      </html>
    );
  }

  return (
    <html lang="ja" className={`${spaceGrotesk.variable} ${jetbrainsMono.variable}`}>
      <head>
        <title>Knowledge Sample | RAG・Memory 技術検証</title>
        <meta name="description" content="Test and compare AWS memory services: AgentCore Memory, Bedrock KB, S3 Vectors" />
      </head>
      <body className="bg-gradient-to-br from-slate-50 to-blue-50 text-slate-800 min-h-screen">
        <ThemeProvider theme={lightTheme}>
          <Authenticator
            hideSignUp={false}
            components={{
              Header() {
                return (
                  <div className="text-center py-6">
                    <h1 className="text-2xl font-bold text-slate-800">🧠 Knowledge Sample</h1>
                    <p className="text-slate-600 text-sm mt-2">RAG・Memory 技術検証</p>
                  </div>
                );
              },
            }}
          >
            {({ signOut, user }) => (
              <div className="min-h-screen bg-white">
                <header className="bg-white border-b border-slate-200 px-4 py-3 flex justify-between items-center shadow-sm">
                  <span className="text-sm text-slate-700 font-medium">
                    👤 {user?.signInDetails?.loginId || user?.username}
                  </span>
                  <button
                    onClick={signOut}
                    className="text-sm bg-slate-700 hover:bg-slate-800 text-white px-4 py-1.5 rounded-md transition-colors"
                  >
                    ログアウト
                  </button>
                </header>
                <main className="bg-slate-50">
                  {children}
                </main>
              </div>
            )}
          </Authenticator>
        </ThemeProvider>
      </body>
    </html>
  );
}




