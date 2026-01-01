"use client";

import { useState } from "react";

interface ServiceCardProps {
  title: string;
  description: string;
  icon: string;
  available: boolean | null;
  operations: {
    name: string;
    endpoint: string;
  }[];
  onTest: (endpoint: string) => Promise<unknown>;
}

export function ServiceCard({
  title,
  description,
  icon,
  available,
  operations,
  onTest,
}: ServiceCardProps) {
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<unknown>(null);
  const [selectedOp, setSelectedOp] = useState(operations[0]?.endpoint || "");

  const handleTest = async () => {
    setLoading(true);
    try {
      const res = await onTest(selectedOp);
      setResult(res);
    } catch (error) {
      setResult({ error: error instanceof Error ? error.message : "Unknown error" });
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="service-card">
      <div className="flex items-start justify-between mb-4">
        <div className="flex items-center gap-3">
          <span className="text-3xl">{icon}</span>
          <div>
            <h3 className="text-xl font-bold text-white">{title}</h3>
            <p className="text-sm text-slate-400">{description}</p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <span className={`status-dot ${available === null ? "checking" : available ? "available" : "unavailable"}`} />
          <span className="text-xs text-slate-400">
            {available === null ? "確認中..." : available ? "利用可能" : "利用不可"}
          </span>
        </div>
      </div>

      <div className="space-y-4">
        <div>
          <label className="block text-sm text-slate-400 mb-2">操作を選択</label>
          <select
            value={selectedOp}
            onChange={(e) => setSelectedOp(e.target.value)}
            className="w-full bg-slate-800 border border-slate-600 rounded-lg px-4 py-2 text-white focus:border-blue-500 focus:outline-none"
          >
            {operations.map((op) => (
              <option key={op.endpoint} value={op.endpoint}>
                {op.name}
              </option>
            ))}
          </select>
        </div>

        <button
          onClick={handleTest}
          disabled={loading || !available}
          className="btn-primary w-full disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {loading ? (
            <span className="flex items-center justify-center gap-2">
              <svg className="animate-spin h-5 w-5" viewBox="0 0 24 24">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
              </svg>
              実行中...
            </span>
          ) : (
            "テスト実行"
          )}
        </button>

        {result !== null && (
          <div className="result-panel">
            <div className="flex items-center justify-between mb-2">
              <span className="text-sm font-semibold text-slate-300">結果</span>
              <button
                onClick={() => setResult(null)}
                className="text-xs text-slate-500 hover:text-slate-300"
              >
                クリア
              </button>
            </div>
            <pre className="code-block text-xs text-emerald-300">
              {JSON.stringify(result, null, 2)}
            </pre>
          </div>
        )}
      </div>
    </div>
  );
}




