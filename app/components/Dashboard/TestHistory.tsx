"use client";

import { useState, useEffect } from "react";

export interface TestResult {
  id: string;
  testCase: "memory" | "multimodal" | "voice";
  operation: string;
  status: "success" | "error";
  timestamp: Date;
  duration: number;
  request: unknown;
  response: unknown;
}

interface TestHistoryProps {
  onSelectResult?: (result: TestResult) => void;
}

const STORAGE_KEY = "rd-knowledge-test-history";

export function TestHistory({ onSelectResult }: TestHistoryProps) {
  const [history, setHistory] = useState<TestResult[]>([]);
  const [filter, setFilter] = useState<"all" | "memory" | "multimodal" | "voice">("all");

  useEffect(() => {
    loadHistory();
  }, []);

  const loadHistory = () => {
    try {
      const stored = localStorage.getItem(STORAGE_KEY);
      if (stored) {
        const parsed = JSON.parse(stored);
        setHistory(
          parsed.map((item: TestResult) => ({
            ...item,
            timestamp: new Date(item.timestamp),
          }))
        );
      }
    } catch (error) {
      console.error("Failed to load history:", error);
    }
  };

  const clearHistory = () => {
    localStorage.removeItem(STORAGE_KEY);
    setHistory([]);
  };

  const filteredHistory = filter === "all" 
    ? history 
    : history.filter((h) => h.testCase === filter);

  const getStatusIcon = (status: string) => {
    return status === "success" ? "✅" : "❌";
  };

  const getTestCaseIcon = (testCase: string) => {
    switch (testCase) {
      case "memory": return "🧠";
      case "multimodal": return "🌈";
      case "voice": return "🎙️";
      default: return "📦";
    }
  };

  const formatDuration = (ms: number) => {
    if (ms < 1000) return `${ms}ms`;
    return `${(ms / 1000).toFixed(2)}s`;
  };

  return (
    <div className="bg-slate-800/50 rounded-xl p-6 border border-slate-700/50">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-lg font-semibold text-white flex items-center gap-2">
          📜 テスト履歴
        </h3>
        <div className="flex gap-2">
          <select
            value={filter}
            onChange={(e) => setFilter(e.target.value as typeof filter)}
            className="px-3 py-1 rounded-lg bg-slate-700 border border-slate-600 text-sm text-white"
          >
            <option value="all">すべて</option>
            <option value="memory">Memory</option>
            <option value="multimodal">Multimodal</option>
            <option value="voice">Voice</option>
          </select>
          <button
            onClick={clearHistory}
            className="px-3 py-1 rounded-lg bg-red-500/20 text-red-400 text-sm hover:bg-red-500/30"
          >
            クリア
          </button>
        </div>
      </div>

      {filteredHistory.length === 0 ? (
        <div className="text-center py-8 text-slate-500">
          <p>テスト履歴がありません</p>
          <p className="text-sm mt-1">テストを実行すると履歴が保存されます</p>
        </div>
      ) : (
        <div className="space-y-2 max-h-64 overflow-y-auto">
          {filteredHistory.slice(0, 20).map((result) => (
            <button
              key={result.id}
              onClick={() => onSelectResult?.(result)}
              className="w-full p-3 rounded-lg bg-slate-700/50 hover:bg-slate-700 transition-colors text-left"
            >
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <span>{getTestCaseIcon(result.testCase)}</span>
                  <span>{getStatusIcon(result.status)}</span>
                  <span className="text-sm text-white">{result.operation}</span>
                </div>
                <span className="text-xs text-slate-400">
                  {formatDuration(result.duration)}
                </span>
              </div>
              <div className="flex items-center justify-between mt-1">
                <span className="text-xs text-slate-500 capitalize">{result.testCase}</span>
                <span className="text-xs text-slate-500">
                  {result.timestamp.toLocaleString()}
                </span>
              </div>
            </button>
          ))}
        </div>
      )}
    </div>
  );
}

// Utility function to save test result
export function saveTestResult(result: Omit<TestResult, "id">) {
  try {
    const stored = localStorage.getItem(STORAGE_KEY);
    const history: TestResult[] = stored ? JSON.parse(stored) : [];
    
    const newResult: TestResult = {
      ...result,
      id: `${Date.now()}-${Math.random().toString(36).substr(2, 9)}`,
    };
    
    history.unshift(newResult);
    
    // Keep only last 100 results
    const trimmed = history.slice(0, 100);
    localStorage.setItem(STORAGE_KEY, JSON.stringify(trimmed));
    
    return newResult;
  } catch (error) {
    console.error("Failed to save test result:", error);
    return null;
  }
}

