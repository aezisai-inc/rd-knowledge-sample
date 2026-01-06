"use client";

import { useState } from "react";
import { MemoryChat } from "./(features)/memory/ui/MemoryChat";
import { MultimodalPanel } from "./(features)/multimodal/ui/MultimodalPanel";
import { VoicePanel } from "./(features)/voice/ui/VoicePanel";

type TabId = "memory" | "multimodal" | "voice";

export default function Home() {
  const [activeTab, setActiveTab] = useState<TabId>("memory");

  const tabs = [
    { id: "memory" as TabId, label: "Memory", icon: "🧠", color: "from-indigo-500 to-blue-500" },
    { id: "multimodal" as TabId, label: "Multimodal", icon: "🎨", color: "from-purple-500 to-pink-500" },
    { id: "voice" as TabId, label: "Voice", icon: "🎤", color: "from-emerald-500 to-teal-500" },
  ];

  return (
    <main className="min-h-screen bg-gray-50">
      {/* Material-style App Bar */}
      <header className="bg-white shadow-sm border-b border-gray-200">
        <div className="max-w-7xl mx-auto px-6 py-4">
          <h1 className="text-xl font-semibold text-gray-900">Knowledge Sample</h1>
          <p className="text-gray-500 text-sm">RAG / Memory 技術検証プラットフォーム</p>
        </div>
      </header>

      {/* Material-style Tab Navigation */}
      <nav className="bg-white border-b border-gray-200 shadow-sm sticky top-0 z-10">
        <div className="max-w-7xl mx-auto px-6">
          <div className="flex gap-2">
            {tabs.map((tab) => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`relative px-6 py-4 text-sm font-medium transition-all duration-200 ${
                  activeTab === tab.id
                    ? "text-blue-600"
                    : "text-gray-600 hover:text-gray-900 hover:bg-gray-50"
                }`}
              >
                <span className="flex items-center gap-2">
                  <span className="text-lg">{tab.icon}</span>
                  {tab.label}
                </span>
                {/* Material-style active indicator */}
                {activeTab === tab.id && (
                  <span className="absolute bottom-0 left-0 right-0 h-0.5 bg-blue-600 rounded-t-full" />
                )}
              </button>
            ))}
          </div>
        </div>
      </nav>

      {/* Content Area */}
      <div className="max-w-7xl mx-auto p-6">
        <div className="bg-white rounded-xl shadow-sm border border-gray-200 overflow-hidden">
          {activeTab === "memory" && <MemoryChat />}
          {activeTab === "multimodal" && <MultimodalPanel />}
          {activeTab === "voice" && <VoicePanel />}
        </div>
      </div>
    </main>
  );
}
