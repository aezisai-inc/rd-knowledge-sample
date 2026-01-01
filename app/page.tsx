"use client";

import { useState, useEffect } from "react";
import { ServiceCard } from "./components/ServiceCard";

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

export default function Home() {
  const [serviceStatus, setServiceStatus] = useState<Record<string, boolean | null>>({});
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    checkAvailability();
  }, []);

  const checkAvailability = async () => {
    setLoading(true);
    try {
      // In real implementation, call the Lambda function
      // For demo, simulate availability check
      const mockStatus: ServiceStatus[] = [
        { service: "bedrock-agentcore-control", available: true },
        { service: "bedrock-agentcore", available: true },
        { service: "bedrock-agent", available: true },
        { service: "bedrock-agent-runtime", available: true },
        { service: "s3vectors", available: true },
      ];

      const status: Record<string, boolean> = {};
      mockStatus.forEach((s) => {
        status[s.service] = s.available;
      });
      setServiceStatus(status);
    } catch (error) {
      console.error("Failed to check availability:", error);
    } finally {
      setLoading(false);
    }
  };

  const handleTest = async (endpoint: string): Promise<unknown> => {
    // In real implementation, call the Lambda function via API Gateway
    // For demo, return mock data
    await new Promise((resolve) => setTimeout(resolve, 500));
    
    const mockResponses: Record<string, unknown> = {
      "/agentcore/create-memory": {
        memoryId: "mem-demo-12345",
        status: "ACTIVE",
        strategies: ["SEMANTIC_MEMORY", "SUMMARY_MEMORY"],
      },
      "/agentcore/create-event": {
        eventId: "evt-demo-67890",
        actorId: "user-123",
        timestamp: new Date().toISOString(),
      },
      "/agentcore/retrieve": {
        records: [],
        message: "No records found (demo mode)",
      },
      "/bedrock-kb/retrieve": {
        results: [
          { content: "Sample document content...", score: 0.95 },
          { content: "Another relevant document...", score: 0.87 },
        ],
      },
      "/s3-vectors/query": {
        vectors: [
          { key: "doc-001", score: 0.92, metadata: { source: "manual.pdf" } },
          { key: "doc-002", score: 0.85, metadata: { source: "guide.pdf" } },
        ],
      },
    };

    return mockResponses[endpoint] || { error: "Unknown endpoint" };
  };

  const getServiceAvailability = (relatedServices: string[]): boolean | null => {
    if (loading) return null;
    return relatedServices.every((s) => serviceStatus[s] === true);
  };

  return (
    <main className="min-h-screen p-8">
      {/* Header */}
      <header className="max-w-6xl mx-auto mb-12 animate-fade-in-up">
        <div className="flex items-center gap-4 mb-4">
          <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-blue-500 to-violet-500 flex items-center justify-center text-2xl">
            🔬
          </div>
          <div>
            <h1 className="text-3xl font-bold bg-gradient-to-r from-blue-400 to-violet-400 bg-clip-text text-transparent">
              Memory Architecture Tester
            </h1>
            <p className="text-slate-400">
              AWS メモリサービスの動作検証・比較ツール
            </p>
          </div>
        </div>

        {/* Decision flowchart summary */}
        <div className="bg-slate-800/50 rounded-xl p-6 border border-slate-700/50 mt-6">
          <h2 className="text-lg font-semibold mb-4 text-slate-200">📋 採用判断クイックガイド</h2>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-sm">
            <div className="flex items-start gap-3">
              <span className="text-2xl">🧠</span>
              <div>
                <p className="font-semibold text-white">AgentCore Memory</p>
                <p className="text-slate-400">「前回の会話を覚えていてほしい」</p>
              </div>
            </div>
            <div className="flex items-start gap-3">
              <span className="text-2xl">📚</span>
              <div>
                <p className="font-semibold text-white">Bedrock KB</p>
                <p className="text-slate-400">「PDF/動画を検索したい」</p>
              </div>
            </div>
            <div className="flex items-start gap-3">
              <span className="text-2xl">🗄️</span>
              <div>
                <p className="font-semibold text-white">S3 Vectors</p>
                <p className="text-slate-400">「100万件を安く保存したい」</p>
              </div>
            </div>
          </div>
        </div>
      </header>

      {/* Service Cards */}
      <div className="max-w-6xl mx-auto grid grid-cols-1 lg:grid-cols-3 gap-6">
        {SERVICES.map((service, index) => (
          <div
            key={service.id}
            className={`animate-fade-in-up delay-${(index + 1) * 100}`}
            style={{ opacity: 0 }}
          >
            <ServiceCard
              title={service.title}
              description={service.description}
              icon={service.icon}
              available={getServiceAvailability(service.relatedServices)}
              operations={service.operations}
              onTest={handleTest}
            />
          </div>
        ))}
      </div>

      {/* Footer */}
      <footer className="max-w-6xl mx-auto mt-12 pt-8 border-t border-slate-800">
        <div className="flex items-center justify-between text-sm text-slate-500">
          <p>rd-knowledge-sample | Amplify Gen2</p>
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




