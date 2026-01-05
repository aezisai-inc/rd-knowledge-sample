"use client";

import { useState, useEffect } from "react";
import { ServiceCard } from "./components/ServiceCard";
import { TestHistory, ResultComparison, type TestResult } from "./components/Dashboard";
import { MultimodalPanel } from "./(features)/multimodal/ui/MultimodalPanel";
import { VoicePanel } from "./(features)/voice/ui/VoicePanel";
import { MemoryChat } from "./(features)/memory/ui/MemoryChat";

interface ServiceStatus {
  service: string;
  available: boolean;
}

const SERVICES = [
  {
    id: "agentcore",
    title: "AgentCore Memory",
    description: "会話履歴・ユーザー体験の保持",
    icon: "🧠",
    operations: [
      { name: "Create Memory", endpoint: "/agentcore/create-memory" },
      { name: "Create Event", endpoint: "/agentcore/create-event" },
      { name: "Retrieve Records", endpoint: "/agentcore/retrieve" },
    ],
    relatedServices: ["bedrock-agentcore-control", "bedrock-agentcore"],
  },
  {
    id: "bedrock-kb",
    title: "Bedrock Knowledge Bases",
    description: "ドキュメントRAG（マネージド）",
    icon: "📚",
    operations: [
      { name: "Retrieve", endpoint: "/bedrock-kb/retrieve" },
    ],
    relatedServices: ["bedrock-agent", "bedrock-agent-runtime"],
  },
  {
    id: "s3-vectors",
    title: "S3 Vectors",
    description: "大量ベクトル保存（低コスト）",
    icon: "🗄️",
    operations: [
      { name: "Query Vectors", endpoint: "/s3-vectors/query" },
    ],
    relatedServices: ["s3vectors"],
  },
];

type TabId = "memory" | "multimodal" | "voice";

export default function Home() {
  const [serviceStatus, setServiceStatus] = useState<Record<string, boolean | null>>({});
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState<TabId>("memory");
  const [comparisonResults, setComparisonResults] = useState<TestResult[]>([]);
  const [showDashboard, setShowDashboard] = useState(false);

  const handleSelectResult = (result: TestResult) => {
    setComparisonResults((prev) => {
      // Limit to 4 results for comparison
      if (prev.some((r) => r.id === result.id)) {
        return prev.filter((r) => r.id !== result.id);
      }
      if (prev.length >= 4) {
        return [...prev.slice(1), result];
      }
      return [...prev, result];
    });
  };

  const clearComparison = () => {
    setComparisonResults([]);
  };

  useEffect(() => {
    checkAvailability();
  }, []);

  const checkAvailability = async () => {
    setLoading(true);
    try {
      // サービス可用性表示（UI表示用の静的ステータス）
      // 実際のサービス可用性は各パネル（MemoryChat, MultimodalPanel, VoicePanel）で
      // GraphQL経由で検証される
      const serviceStatuses: ServiceStatus[] = [
        { service: "bedrock-agentcore-control", available: true },
        { service: "bedrock-agentcore", available: true },
        { service: "bedrock-agent", available: true },
        { service: "bedrock-agent-runtime", available: true },
        { service: "s3vectors", available: true },
      ];

      const status: Record<string, boolean> = {};
      serviceStatuses.forEach((s) => {
        status[s.service] = s.available;
      });
      setServiceStatus(status);
    } catch (error) {
      console.error("Failed to check availability:", error);
    } finally {
      setLoading(false);
    }
  };

  // Legacy API test handler - ServiceCard tests are informational only
  // Main functionality uses GraphQL via MemoryChat, MultimodalPanel, VoicePanel
  const handleTest = async (endpoint: string): Promise<unknown> => {
    // ServiceCard tests are deprecated - use the GraphQL-based panels instead
    return { 
      message: "この機能は GraphQL に移行しました。Memory/Multimodal/Voice タブをご利用ください。",
      endpoint,
      deprecated: true
    };
  };

  const getServiceAvailability = (relatedServices: string[]): boolean | null => {
    if (loading) return null;
    return relatedServices.every((s) => serviceStatus[s] === true);
  };

  return (
    <main className="min-h-screen p-8">
      {/* Header */}
      <header className="max-w-6xl mx-auto mb-12 animate-fade-in-up">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-4">
            <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-blue-500 to-violet-500 flex items-center justify-center text-2xl">
              🔬
            </div>
            <div>
              <h1 className="text-3xl font-bold bg-gradient-to-r from-blue-400 to-violet-400 bg-clip-text text-transparent">
                AWS Nova テストダッシュボード
              </h1>
              <p className="text-slate-400">
                Memory / Multimodal / Voice の技術検証
              </p>
            </div>
          </div>
          <button
            onClick={() => setShowDashboard(!showDashboard)}
            className={`px-4 py-2 rounded-lg transition-all ${
              showDashboard
                ? "bg-violet-500 text-white"
                : "bg-slate-700 text-slate-300 hover:bg-slate-600"
            }`}
          >
            📊 {showDashboard ? "ダッシュボード非表示" : "ダッシュボード表示"}
          </button>
        </div>

        {/* Tab Navigation */}
        <div className="flex gap-2 mt-6 p-1 bg-slate-800/50 rounded-xl border border-slate-700/50">
          {[
            { id: "memory" as TabId, label: "Memory", icon: "🧠", description: "AgentCore Memory テスト" },
            { id: "multimodal" as TabId, label: "Multimodal", icon: "🌈", description: "Nova Vision/Canvas/Reel" },
            { id: "voice" as TabId, label: "Voice", icon: "🎙️", description: "Nova Sonic 音声対話" },
          ].map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`flex-1 py-3 px-4 rounded-lg text-sm font-medium transition-all ${
                activeTab === tab.id
                  ? "bg-gradient-to-r from-blue-500 to-violet-500 text-white shadow-lg"
                  : "text-slate-400 hover:text-white hover:bg-slate-700/50"
              }`}
            >
              <span className="text-lg mr-2">{tab.icon}</span>
              {tab.label}
            </button>
          ))}
        </div>
      </header>

      {/* Tab Content */}
      <div className="max-w-6xl mx-auto">
        {/* Memory Tab */}
        {activeTab === "memory" && (
          <div className="bg-slate-800/50 rounded-xl border border-slate-700/50 min-h-[700px]">
            <MemoryChat />
          </div>
        )}

        {/* Multimodal Tab */}
        {activeTab === "multimodal" && (
          <div className="bg-slate-800/50 rounded-xl border border-slate-700/50 min-h-[600px]">
            <MultimodalPanel />
          </div>
        )}

        {/* Voice Tab */}
        {activeTab === "voice" && (
          <div className="bg-slate-800/50 rounded-xl border border-slate-700/50 min-h-[600px]">
            <VoicePanel />
          </div>
        )}
      </div>

      {/* Dashboard Section */}
      {showDashboard && (
        <div className="max-w-6xl mx-auto mt-8 grid grid-cols-1 lg:grid-cols-2 gap-6">
          <TestHistory onSelectResult={handleSelectResult} />
          <ResultComparison results={comparisonResults} onClear={clearComparison} />
        </div>
      )}

      {/* Footer */}
      <footer className="max-w-6xl mx-auto mt-12 pt-8 border-t border-slate-800">
        <div className="flex items-center justify-between text-sm text-slate-500">
          <p>rd-knowledge-sample | AWS Nova Series 技術検証</p>
          <div className="flex items-center gap-4">
            <button
              onClick={checkAvailability}
              className="hover:text-slate-300 transition-colors"
            >
              🔄 再チェック
            </button>
            <a
              href="https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/memory.html"
              target="_blank"
              rel="noopener noreferrer"
              className="hover:text-slate-300 transition-colors"
            >
              📖 ドキュメント
            </a>
          </div>
        </div>
      </footer>
    </main>
  );
}




