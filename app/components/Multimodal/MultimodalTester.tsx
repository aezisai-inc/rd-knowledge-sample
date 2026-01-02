"use client";

import { useState, useRef, ChangeEvent } from "react";

interface MultimodalTesterProps {
  apiBaseUrl: string;
}

type TestMode = "understand-image" | "generate-image" | "understand-video" | "generate-video";

interface TestResult {
  success: boolean;
  data?: unknown;
  error?: string;
  timestamp: string;
}

export function MultimodalTester({ apiBaseUrl }: MultimodalTesterProps) {
  const [mode, setMode] = useState<TestMode>("understand-image");
  const [prompt, setPrompt] = useState("");
  const [imageData, setImageData] = useState<string | null>(null);
  const [videoUri, setVideoUri] = useState("");
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<TestResult | null>(null);
  const [generatedImage, setGeneratedImage] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleImageUpload = (e: ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    const reader = new FileReader();
    reader.onload = () => {
      const base64 = (reader.result as string).split(",")[1];
      setImageData(base64);
    };
    reader.readAsDataURL(file);
  };

  const handleTest = async () => {
    setLoading(true);
    setResult(null);
    setGeneratedImage(null);

    try {
      let response: Response;
      let body: object;

      switch (mode) {
        case "understand-image":
          if (!imageData) {
            throw new Error("画像を選択してください");
          }
          body = {
            message: prompt || "この画像を説明してください",
            images: [imageData],
          };
          response = await fetch(`${apiBaseUrl}/v1/agent/multimodal/invoke`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(body),
          });
          break;

        case "generate-image":
          if (!prompt) {
            throw new Error("プロンプトを入力してください");
          }
          body = {
            message: `以下のプロンプトで画像を生成してください: ${prompt}`,
          };
          response = await fetch(`${apiBaseUrl}/v1/agent/multimodal/invoke`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(body),
          });
          break;

        case "understand-video":
          if (!videoUri) {
            throw new Error("動画の S3 URI を入力してください");
          }
          body = {
            message: prompt || "この動画を要約してください",
            videos: [videoUri],
          };
          response = await fetch(`${apiBaseUrl}/v1/agent/multimodal/invoke`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(body),
          });
          break;

        case "generate-video":
          if (!prompt) {
            throw new Error("プロンプトを入力してください");
          }
          body = {
            message: `以下のプロンプトで動画を生成してください: ${prompt}`,
          };
          response = await fetch(`${apiBaseUrl}/v1/agent/multimodal/invoke`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(body),
          });
          break;

        default:
          throw new Error("不明なモード");
      }

      if (!response.ok) {
        const errorText = await response.text();
        throw new Error(`HTTP ${response.status}: ${errorText}`);
      }

      const data = await response.json();

      // 画像生成結果の処理
      if (mode === "generate-image" && data.images?.[0]?.base64) {
        setGeneratedImage(data.images[0].base64);
      }

      setResult({
        success: true,
        data,
        timestamp: new Date().toISOString(),
      });
    } catch (error) {
      setResult({
        success: false,
        error: error instanceof Error ? error.message : "Unknown error",
        timestamp: new Date().toISOString(),
      });
    } finally {
      setLoading(false);
    }
  };

  const modes: { id: TestMode; label: string; icon: string; description: string }[] = [
    { id: "understand-image", label: "画像理解", icon: "🔍", description: "画像の内容を分析" },
    { id: "generate-image", label: "画像生成", icon: "🎨", description: "テキストから画像生成" },
    { id: "understand-video", label: "動画理解", icon: "📹", description: "動画の内容を分析" },
    { id: "generate-video", label: "動画生成", icon: "🎬", description: "テキストから動画生成" },
  ];

  return (
    <div className="bg-gradient-to-br from-slate-800/80 to-slate-900/80 rounded-2xl p-6 border border-slate-700/50 shadow-xl">
      {/* Header */}
      <div className="flex items-center gap-3 mb-6">
        <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-purple-500 to-pink-500 flex items-center justify-center text-xl">
          🌈
        </div>
        <div>
          <h2 className="text-xl font-bold text-white">Multimodal Tester</h2>
          <p className="text-sm text-slate-400">Nova Vision / Canvas / Reel</p>
        </div>
      </div>

      {/* Mode Selector */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-2 mb-6">
        {modes.map((m) => (
          <button
            key={m.id}
            onClick={() => setMode(m.id)}
            className={`p-3 rounded-xl text-left transition-all ${
              mode === m.id
                ? "bg-purple-500/20 border-purple-500 border"
                : "bg-slate-700/50 border-slate-600/50 border hover:bg-slate-700"
            }`}
          >
            <span className="text-2xl">{m.icon}</span>
            <p className="text-sm font-medium text-white mt-1">{m.label}</p>
            <p className="text-xs text-slate-400">{m.description}</p>
          </button>
        ))}
      </div>

      {/* Input Area */}
      <div className="space-y-4 mb-6">
        {/* Image Upload (for understand-image) */}
        {mode === "understand-image" && (
          <div>
            <label className="block text-sm font-medium text-slate-300 mb-2">
              画像をアップロード
            </label>
            <div
              onClick={() => fileInputRef.current?.click()}
              className={`border-2 border-dashed rounded-xl p-6 text-center cursor-pointer transition-colors ${
                imageData
                  ? "border-purple-500 bg-purple-500/10"
                  : "border-slate-600 hover:border-slate-500"
              }`}
            >
              {imageData ? (
                <div className="space-y-2">
                  <img
                    src={`data:image/png;base64,${imageData}`}
                    alt="Uploaded"
                    className="max-h-48 mx-auto rounded-lg"
                  />
                  <p className="text-sm text-slate-400">クリックで変更</p>
                </div>
              ) : (
                <div className="space-y-2">
                  <span className="text-4xl">📷</span>
                  <p className="text-slate-400">クリックして画像を選択</p>
                  <p className="text-xs text-slate-500">PNG, JPG, GIF</p>
                </div>
              )}
            </div>
            <input
              ref={fileInputRef}
              type="file"
              accept="image/*"
              onChange={handleImageUpload}
              className="hidden"
            />
          </div>
        )}

        {/* Video URI (for understand-video) */}
        {mode === "understand-video" && (
          <div>
            <label className="block text-sm font-medium text-slate-300 mb-2">
              動画 S3 URI
            </label>
            <input
              type="text"
              value={videoUri}
              onChange={(e) => setVideoUri(e.target.value)}
              placeholder="s3://bucket-name/path/to/video.mp4"
              className="w-full px-4 py-3 rounded-xl bg-slate-700/50 border border-slate-600 text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-purple-500"
            />
          </div>
        )}

        {/* Prompt */}
        <div>
          <label className="block text-sm font-medium text-slate-300 mb-2">
            {mode.includes("generate") ? "生成プロンプト" : "質問（オプション）"}
          </label>
          <textarea
            value={prompt}
            onChange={(e) => setPrompt(e.target.value)}
            placeholder={
              mode === "generate-image"
                ? "富士山と桜の美しい風景、朝日が昇る"
                : mode === "generate-video"
                ? "海辺で波が静かに打ち寄せる様子、夕暮れ時"
                : "この画像/動画について説明してください"
            }
            rows={3}
            className="w-full px-4 py-3 rounded-xl bg-slate-700/50 border border-slate-600 text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-purple-500 resize-none"
          />
        </div>
      </div>

      {/* Execute Button */}
      <button
        onClick={handleTest}
        disabled={loading}
        className={`w-full py-3 rounded-xl font-semibold transition-all ${
          loading
            ? "bg-slate-600 cursor-not-allowed"
            : "bg-gradient-to-r from-purple-500 to-pink-500 hover:from-purple-600 hover:to-pink-600"
        } text-white`}
      >
        {loading ? (
          <span className="flex items-center justify-center gap-2">
            <svg className="animate-spin h-5 w-5" viewBox="0 0 24 24">
              <circle
                className="opacity-25"
                cx="12"
                cy="12"
                r="10"
                stroke="currentColor"
                strokeWidth="4"
                fill="none"
              />
              <path
                className="opacity-75"
                fill="currentColor"
                d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"
              />
            </svg>
            処理中...
          </span>
        ) : (
          `${modes.find((m) => m.id === mode)?.icon} 実行`
        )}
      </button>

      {/* Generated Image Preview */}
      {generatedImage && (
        <div className="mt-6 p-4 bg-slate-700/30 rounded-xl">
          <h3 className="text-sm font-medium text-slate-300 mb-3">生成された画像</h3>
          <img
            src={`data:image/png;base64,${generatedImage}`}
            alt="Generated"
            className="max-h-64 mx-auto rounded-lg shadow-lg"
          />
        </div>
      )}

      {/* Result */}
      {result && (
        <div
          className={`mt-6 p-4 rounded-xl ${
            result.success ? "bg-green-500/10 border border-green-500/30" : "bg-red-500/10 border border-red-500/30"
          }`}
        >
          <div className="flex items-center gap-2 mb-2">
            <span>{result.success ? "✅" : "❌"}</span>
            <span className={result.success ? "text-green-400" : "text-red-400"}>
              {result.success ? "成功" : "エラー"}
            </span>
            <span className="text-xs text-slate-500 ml-auto">{result.timestamp}</span>
          </div>
          <pre className="text-xs text-slate-300 overflow-auto max-h-48 bg-slate-800/50 p-3 rounded-lg">
            {result.success
              ? JSON.stringify(result.data, null, 2)
              : result.error}
          </pre>
        </div>
      )}
    </div>
  );
}

