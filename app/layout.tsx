"use client";

import { useState, useEffect } from "react";
import { Amplify } from "aws-amplify";
import "./globals.css";
import { Authenticator, ThemeProvider, Theme } from "@aws-amplify/ui-react";
import "@aws-amplify/ui-react/styles.css";
import outputs from "./amplify_outputs.json";

// Material UI風カスタムテーマ
const materialTheme: Theme = {
  name: 'material-light',
  tokens: {
    colors: {
      background: {
        primary: { value: '#ffffff' },
        secondary: { value: '#f5f5f5' },
      },
      font: {
        primary: { value: '#212121' },
        secondary: { value: '#757575' },
      },
      brand: {
        primary: {
          '10': { value: '#e3f2fd' },
          '80': { value: '#1976d2' },
          '90': { value: '#1565c0' },
          '100': { value: '#0d47a1' },
        },
      },
    },
    components: {
      authenticator: {
        router: {
          borderWidth: { value: '0' },
          boxShadow: { value: '0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06)' },
        },
      },
      button: {
        primary: {
          backgroundColor: { value: '{colors.brand.primary.80}' },
          _hover: {
            backgroundColor: { value: '{colors.brand.primary.90}' },
          },
        },
      },
    },
  },
};

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
        <body className="bg-gray-50 text-gray-900 min-h-screen flex items-center justify-center">
          <div className="text-center">
            <div className="w-10 h-10 border-4 border-blue-500 border-t-transparent rounded-full animate-spin mx-auto mb-4"></div>
            <p className="text-gray-500">読み込み中...</p>
          </div>
        </body>
      </html>
    );
  }

  return (
    <html lang="ja">
      <head>
        <title>Knowledge Sample | RAG Memory Platform</title>
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="anonymous" />
        <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet" />
      </head>
      <body className="bg-gray-50 text-gray-900 min-h-screen font-[Inter,system-ui,sans-serif]">
        <ThemeProvider theme={materialTheme}>
          <Authenticator
            hideSignUp={false}
            components={{
              Header() {
                return (
                  <div className="text-center py-8 bg-white">
                    <h1 className="text-2xl font-bold text-gray-900">Knowledge Sample</h1>
                    <p className="text-gray-500 text-sm mt-2">RAG / Memory 技術検証</p>
                  </div>
                );
              },
            }}
          >
            {({ signOut, user }) => (
              <div className="min-h-screen bg-gray-50">
                {/* Material-style Top App Bar */}
                <header className="bg-white border-b border-gray-200 px-6 py-3 flex justify-between items-center shadow-sm">
                  <div className="flex items-center gap-3">
                    <div className="w-8 h-8 bg-blue-500 rounded-full flex items-center justify-center text-white text-sm font-medium">
                      {(user?.signInDetails?.loginId || user?.username || 'U')[0].toUpperCase()}
                    </div>
                    <span className="text-gray-700 text-sm font-medium">
                      {user?.signInDetails?.loginId || user?.username}
                    </span>
                  </div>
                  <button
                    onClick={signOut}
                    className="text-sm text-gray-600 hover:text-gray-900 hover:bg-gray-100 px-4 py-2 rounded-lg transition-colors"
                  >
                    ログアウト
                  </button>
                </header>
                <main>{children}</main>
              </div>
            )}
          </Authenticator>
        </ThemeProvider>
      </body>
    </html>
  );
}
