"use client";

import { useState } from "react";
import { MemoryChat } from "./(features)/memory/ui/MemoryChat";
import { MultimodalPanel } from "./(features)/multimodal/ui/MultimodalPanel";
import { VoicePanel } from "./(features)/voice/ui/VoicePanel";

type TabId = "memory" | "multimodal" | "voice";

export default function Home() {
  const [activeTab, setActiveTab] = useState<TabId>("memory");

  const tabs = [
    { id: "memory" as TabId, label: "Memory", icon: "🧠" },
    { id: "multimodal" as TabId, label: "Multimodal", icon: "🎨" },
    { id: "voice" as TabId, label: "Voice", icon: "🎤" },
  ];

  return (
    <main className="min-h-screen bg-slate-900">
      {/* Header */}
      <header className="bg-slate-800 border-b border-slate-700 px-6 py-4">
        <h1 className="text-xl font-semibold text-white">Knowledge Sample</h1>
        <p className="text-slate-400 text-sm">RAG / Memory 技術検証</p>
      </header>

      {/* Tab Navigation */}
      <nav className="bg-slate-800 border-b border-slate-700 px-6">
        <div className="flex gap-1">
          {tabs.map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`px-4 py-3 text-sm font-medium border-b-2 transition-colors ${
                activeTab === tab.id
                  ? "text-white border-blue-500"
                  : "text-slate-400 border-transparent hover:text-slate-200"
              }`}
            >
              <span className="mr-2">{tab.icon}</span>
              {tab.label}
            </button>
          ))}
        </div>
      </nav>

      {/* Content */}
      <div className="p-6">
        {activeTab === "memory" && <MemoryChat />}
        {activeTab === "multimodal" && <MultimodalPanel />}
        {activeTab === "voice" && <VoicePanel />}
      </div>
    </main>
  );
}
