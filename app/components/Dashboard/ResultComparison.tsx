"use client";

import { useState } from "react";
import type { TestResult } from "./TestHistory";

interface ResultComparisonProps {
  results: TestResult[];
  onClear: () => void;
}

export function ResultComparison({ results, onClear }: ResultComparisonProps) {
  const [viewMode, setViewMode] = useState<"side-by-side" | "diff">("side-by-side");

  if (results.length === 0) {
    return (
      <div className="bg-slate-800/50 rounded-xl p-6 border border-slate-700/50">
        <h3 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
          ⚖️ 結果比較
        </h3>
        <div className="text-center py-8 text-slate-500">
          <p>比較する結果を選択してください</p>
          <p className="text-sm mt-1">テスト履歴から結果をクリックして追加</p>
        </div>
      </div>
    );
  }

  const getStatusColor = (status: string) => {
    return status === "success" ? "text-green-400" : "text-red-400";
  };

  const getTestCaseIcon = (testCase: string) => {
    switch (testCase) {
      case "memory": return "🧠";
      case "multimodal": return "🌈";
      case "voice": return "🎙️";
      default: return "📦";
    }
  };

  const formatJson = (data: unknown) => {
    try {
      return JSON.stringify(data, null, 2);
    } catch {
      return String(data);
    }
  };

  return (
    <div className="bg-slate-800/50 rounded-xl p-6 border border-slate-700/50">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-lg font-semibold text-white flex items-center gap-2">
          ⚖️ 結果比較 ({results.length}件)
        </h3>
        <div className="flex gap-2">
          <select
            value={viewMode}
            onChange={(e) => setViewMode(e.target.value as typeof viewMode)}
            className="px-3 py-1 rounded-lg bg-slate-700 border border-slate-600 text-sm text-white"
          >
            <option value="side-by-side">並列表示</option>
            <option value="diff">差分表示</option>
          </select>
          <button
            onClick={onClear}
            className="px-3 py-1 rounded-lg bg-slate-600 text-white text-sm hover:bg-slate-500"
          >
            クリア
          </button>
        </div>
      </div>

      {viewMode === "side-by-side" ? (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 max-h-96 overflow-y-auto">
          {results.map((result, index) => (
            <div
              key={result.id}
              className="p-4 rounded-lg bg-slate-700/50 border border-slate-600"
            >
              <div className="flex items-center gap-2 mb-2">
                <span className="text-sm font-mono text-slate-400">#{index + 1}</span>
                <span>{getTestCaseIcon(result.testCase)}</span>
                <span className={`font-medium ${getStatusColor(result.status)}`}>
                  {result.status === "success" ? "成功" : "エラー"}
                </span>
              </div>
              
              <div className="space-y-2 text-sm">
                <div>
                  <span className="text-slate-400">操作:</span>
                  <span className="ml-2 text-white">{result.operation}</span>
                </div>
                <div>
                  <span className="text-slate-400">時間:</span>
                  <span className="ml-2 text-white">{result.duration}ms</span>
                </div>
                <div>
                  <span className="text-slate-400">実行日時:</span>
                  <span className="ml-2 text-white">
                    {result.timestamp.toLocaleString()}
                  </span>
                </div>
              </div>

              <div className="mt-3">
                <p className="text-xs text-slate-400 mb-1">レスポンス:</p>
                <pre className="text-xs text-slate-300 bg-slate-800 p-2 rounded overflow-auto max-h-32">
                  {formatJson(result.response)}
                </pre>
              </div>
            </div>
          ))}
        </div>
      ) : (
        <div className="space-y-4">
          {/* Summary comparison */}
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-slate-600">
                  <th className="text-left py-2 text-slate-400">項目</th>
                  {results.map((_, i) => (
                    <th key={i} className="text-left py-2 text-slate-400">
                      結果 #{i + 1}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                <tr className="border-b border-slate-700">
                  <td className="py-2 text-slate-300">テストケース</td>
                  {results.map((r) => (
                    <td key={r.id} className="py-2 text-white capitalize">
                      {getTestCaseIcon(r.testCase)} {r.testCase}
                    </td>
                  ))}
                </tr>
                <tr className="border-b border-slate-700">
                  <td className="py-2 text-slate-300">ステータス</td>
                  {results.map((r) => (
                    <td key={r.id} className={`py-2 ${getStatusColor(r.status)}`}>
                      {r.status === "success" ? "✅ 成功" : "❌ エラー"}
                    </td>
                  ))}
                </tr>
                <tr className="border-b border-slate-700">
                  <td className="py-2 text-slate-300">所要時間</td>
                  {results.map((r) => (
                    <td key={r.id} className="py-2 text-white">
                      {r.duration}ms
                    </td>
                  ))}
                </tr>
                <tr className="border-b border-slate-700">
                  <td className="py-2 text-slate-300">操作</td>
                  {results.map((r) => (
                    <td key={r.id} className="py-2 text-white">
                      {r.operation}
                    </td>
                  ))}
                </tr>
              </tbody>
            </table>
          </div>

          {/* Response diff */}
          <div>
            <p className="text-sm text-slate-400 mb-2">レスポンス比較:</p>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
              {results.map((r, i) => (
                <div key={r.id}>
                  <p className="text-xs text-slate-500 mb-1">結果 #{i + 1}</p>
                  <pre className="text-xs text-slate-300 bg-slate-800 p-2 rounded overflow-auto max-h-48">
                    {formatJson(r.response)}
                  </pre>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

