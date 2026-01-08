'use client';

import React, { useState, useCallback, useRef, useMemo } from 'react';
import { generateClient } from 'aws-amplify/data';
import type { Schema } from '../../../../amplify/data/resource';

type TabId = 'analyze' | 'generate-image' | 'generate-video';

interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: string;
  inputImage?: string; // base64 of uploaded image
  outputImages?: { base64: string; seed?: number }[];
  outputVideo?: { status: string; jobId?: string; url?: string };
}

export function MultimodalPanel() {
  // Amplify clientを遅延初期化（Amplify.configure後に呼び出されることを保証）
  // 認証モードをapiKeyに明示的に設定（publicApiKey認可を使用するため）
  const client = useMemo(() => generateClient<Schema>({ authMode: 'apiKey' }), []);
  
  const [activeTab, setActiveTab] = useState<TabId>('analyze');
  const [sessionId] = useState(() => `multimodal-${Date.now()}`);
  const [prompt, setPrompt] = useState('');
  const [messages, setMessages] = useState<Message[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [uploadedImage, setUploadedImage] = useState<string | null>(null);
  const [uploadedFileName, setUploadedFileName] = useState<string | null>(null);
  
  const fileInputRef = useRef<HTMLInputElement>(null);

  // =============================================================================
  // Image Upload
  // =============================================================================

  const handleImageUpload = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    // Validate file type
    if (!file.type.startsWith('image/')) {
      alert('画像ファイルを選択してください');
      return;
    }

    // Validate file size (max 5MB)
    if (file.size > 5 * 1024 * 1024) {
      alert('ファイルサイズは5MB以下にしてください');
      return;
    }

    const reader = new FileReader();
    reader.onload = (event) => {
      const base64 = event.target?.result as string;
      // Remove data:image/xxx;base64, prefix for API
      const base64Data = base64.split(',')[1];
      setUploadedImage(base64Data);
      setUploadedFileName(file.name);
    };
    reader.readAsDataURL(file);
  }, []);

  const clearUploadedImage = useCallback(() => {
    setUploadedImage(null);
    setUploadedFileName(null);
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  }, []);

  // =============================================================================
  // Submit Handler
  // =============================================================================

  const handleSubmit = useCallback(async () => {
    if (isLoading) return;
    
    // Validation based on tab
    if (activeTab === 'analyze' && !prompt.trim() && !uploadedImage) {
      alert('プロンプトまたは画像をアップロードしてください');
      return;
    }
    if ((activeTab === 'generate-image' || activeTab === 'generate-video') && !prompt.trim()) {
      alert('生成するコンテンツの説明を入力してください');
      return;
    }

    const userMessage: Message = {
      id: `user-${Date.now()}`,
      role: 'user',
      content: prompt || (uploadedImage ? '画像を解析してください' : ''),
      timestamp: new Date().toISOString(),
      inputImage: uploadedImage || undefined,
    };

    setMessages((prev) => [...prev, userMessage]);
    const currentPrompt = prompt;
    setPrompt('');
    setIsLoading(true);

    try {
      let assistantMessage: Message;

      // Helper to extract message from various response structures
      const extractMessage = (res: any) => 
        res?.data?.message || 
        res?.data?.invokeMultimodal?.message || 
        res?.invokeMultimodal?.message;
      
      const extractData = (res: any) =>
        res?.data || res?.data?.invokeMultimodal || res?.invokeMultimodal;

      if (activeTab === 'analyze') {
        // =============================================================================
        // Image Analysis (Nova Vision)
        // =============================================================================
        const response = await client.mutations.invokeMultimodal({
          sessionId,
          prompt: currentPrompt || 'この画像を詳しく説明してください。',
          image: uploadedImage || undefined,
        });

        console.log('[MultimodalPanel] Response:', JSON.stringify(response, null, 2));

        assistantMessage = {
          id: `assistant-${Date.now()}`,
          role: 'assistant',
          content: extractMessage(response) || 'No response received',
          timestamp: new Date().toISOString(),
        };

      } else if (activeTab === 'generate-image') {
        // =============================================================================
        // Image Generation (Nova Canvas)
        // =============================================================================
        const response = await client.mutations.invokeMultimodal({
          sessionId,
          prompt: `[IMAGE_GENERATION] ${currentPrompt}`,
        });

        console.log('[MultimodalPanel] Image Response:', JSON.stringify(response, null, 2));
        const data = extractData(response);
        const images = data?.images?.filter(
          (img: any): img is { base64: string; seed?: number } => !!img?.base64
        ) || [];

        assistantMessage = {
          id: `assistant-${Date.now()}`,
          role: 'assistant',
          content: extractMessage(response) || (images.length > 0 ? `${images.length}枚の画像を生成しました` : '画像生成に失敗しました'),
          timestamp: new Date().toISOString(),
          outputImages: images.length > 0 ? images : undefined,
        };

      } else {
        // =============================================================================
        // Video Generation (Nova Reel)
        // =============================================================================
        const response = await client.mutations.invokeMultimodal({
          sessionId,
          prompt: `[VIDEO_GENERATION] ${currentPrompt}`,
        });

        console.log('[MultimodalPanel] Video Response:', JSON.stringify(response, null, 2));
        const data = extractData(response);
        assistantMessage = {
          id: `assistant-${Date.now()}`,
          role: 'assistant',
          content: extractMessage(response) || '動画生成ジョブを開始しました',
          timestamp: new Date().toISOString(),
          outputVideo: data?.video ? {
            status: data.video.status || 'PENDING',
            jobId: data.video.jobId ?? undefined,
            url: data.video.url ?? undefined,
          } : { status: 'PENDING' },
        };
      }

      setMessages((prev) => [...prev, assistantMessage]);
      clearUploadedImage();

    } catch (error) {
      console.error('Multimodal request failed:', error);
      const errorMessage: Message = {
        id: `error-${Date.now()}`,
        role: 'assistant',
        content: `Error: ${error instanceof Error ? error.message : 'Unknown error'}`,
        timestamp: new Date().toISOString(),
      };
      setMessages((prev) => [...prev, errorMessage]);
    } finally {
      setIsLoading(false);
    }
  }, [prompt, sessionId, isLoading, uploadedImage, activeTab, clearUploadedImage]);

  // =============================================================================
  // Tab Configuration
  // =============================================================================

  const tabs: { id: TabId; label: string; icon: string; description: string }[] = [
    { id: 'analyze', label: '画像解析', icon: '👁️', description: 'Nova Vision' },
    { id: 'generate-image', label: '画像生成', icon: '🎨', description: 'Nova Canvas' },
    { id: 'generate-video', label: '動画生成', icon: '🎬', description: 'Nova Reel' },
  ];

  // =============================================================================
  // Render
  // =============================================================================

  return (
    <div className="h-[700px] flex flex-col bg-gray-50">
      {/* Tab Navigation */}
      <div className="flex border-b border-gray-200 bg-white">
        {tabs.map((tab) => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            className={`flex-1 px-4 py-3 text-sm font-medium transition-colors ${
              activeTab === tab.id
                ? 'text-blue-600 border-b-2 border-blue-600 bg-blue-50'
                : 'text-gray-600 hover:text-gray-900 hover:bg-gray-100'
            }`}
          >
            <span className="text-lg mr-2">{tab.icon}</span>
            {tab.label}
            <span className="block text-xs text-gray-500">{tab.description}</span>
          </button>
        ))}
      </div>

      {/* Messages Area */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {messages.length === 0 ? (
          <div className="h-full flex flex-col items-center justify-center text-gray-500">
            {activeTab === 'analyze' ? (
              <>
                <p className="text-4xl mb-4">👁️</p>
                <p className="text-lg font-medium text-gray-700">画像解析</p>
                <p className="text-sm mt-2">画像をアップロードして、AIに解析してもらいましょう</p>
              </>
            ) : activeTab === 'generate-image' ? (
              <>
                <p className="text-4xl mb-4">🎨</p>
                <p className="text-lg font-medium text-gray-700">画像生成</p>
                <p className="text-sm mt-2">テキストから画像を生成します</p>
              </>
            ) : (
              <>
                <p className="text-4xl mb-4">🎬</p>
                <p className="text-lg font-medium text-gray-700">動画生成</p>
                <p className="text-sm mt-2">テキストから動画を生成します（非同期処理）</p>
              </>
            )}
          </div>
        ) : (
          messages.map((message) => (
            <div
              key={message.id}
              className={`flex ${message.role === 'user' ? 'justify-end' : 'justify-start'}`}
            >
              <div
                className={`max-w-[80%] rounded-xl p-4 ${
                  message.role === 'user'
                    ? 'bg-blue-500 text-white'
                    : 'bg-white border border-gray-200 text-gray-800 shadow-sm'
                }`}
              >
                {/* User's uploaded image */}
                {message.inputImage && (
                  <div className="mb-3">
                    <img
                      src={`data:image/png;base64,${message.inputImage}`}
                      alt="Uploaded"
                      className="max-w-full max-h-64 rounded-lg"
                    />
                  </div>
                )}
                
                <p className="whitespace-pre-wrap">{message.content}</p>
                
                {/* Generated images */}
                {message.outputImages && message.outputImages.length > 0 && (
                  <div className="mt-4 grid grid-cols-1 gap-4">
                    {message.outputImages.map((img, idx) => (
                      <div key={idx} className="relative">
                        <img
                          src={`data:image/png;base64,${img.base64}`}
                          alt={`Generated ${idx + 1}`}
                          className="max-w-full rounded-lg"
                        />
                        {img.seed && (
                          <span className="absolute bottom-2 right-2 bg-black/50 text-white text-xs px-2 py-1 rounded">
                            Seed: {img.seed}
                          </span>
                        )}
                        <a
                          href={`data:image/png;base64,${img.base64}`}
                          download={`generated-${Date.now()}.png`}
                          className="absolute top-2 right-2 bg-black/50 text-white text-xs px-2 py-1 rounded hover:bg-black/70"
                        >
                          💾 保存
                        </a>
                      </div>
                    ))}
                  </div>
                )}

                {/* Video generation status */}
                {message.outputVideo && (
                  <div className="mt-4 p-3 bg-gray-50 rounded-lg border border-gray-200">
                    <div className="flex items-center gap-2">
                      <span className={`w-2 h-2 rounded-full ${
                        message.outputVideo.status === 'COMPLETED' ? 'bg-green-500' :
                        message.outputVideo.status === 'FAILED' ? 'bg-red-500' :
                        'bg-yellow-500 animate-pulse'
                      }`} />
                      <span className="text-sm text-gray-700">Status: {message.outputVideo.status}</span>
                    </div>
                    {message.outputVideo.jobId && (
                      <p className="text-xs text-gray-500 mt-1">Job ID: {message.outputVideo.jobId}</p>
                    )}
                    {message.outputVideo.url && (
                      <a
                        href={message.outputVideo.url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-blue-600 text-sm mt-2 inline-block hover:underline"
                      >
                        🎬 動画を見る
                      </a>
                    )}
                  </div>
                )}

                <p className="text-xs mt-2 opacity-70">
                  {new Date(message.timestamp).toLocaleTimeString()}
                </p>
              </div>
            </div>
          ))
        )}
        {isLoading && (
          <div className="flex items-center gap-2 text-gray-600 justify-center py-4">
            <div className="w-5 h-5 border-2 border-blue-500 border-t-transparent rounded-full animate-spin" />
            <span className="text-sm">
              {activeTab === 'analyze' ? '画像を解析中...' :
               activeTab === 'generate-image' ? '画像を生成中...' :
               '動画生成ジョブを作成中...'}
            </span>
          </div>
        )}
      </div>

      {/* Input Area */}
      <div className="border-t border-gray-200 p-4 bg-white">
        {/* Image Upload (for analyze tab) */}
        {activeTab === 'analyze' && (
          <div className="mb-3">
            <input
              ref={fileInputRef}
              type="file"
              accept="image/*"
              onChange={handleImageUpload}
              className="hidden"
              id="image-upload"
            />
            
            {uploadedImage ? (
              <div className="flex items-center gap-3 p-3 bg-gray-100 rounded-lg border border-gray-200">
                <img
                  src={`data:image/png;base64,${uploadedImage}`}
                  alt="Preview"
                  className="w-16 h-16 object-cover rounded"
                />
                <div className="flex-1">
                  <p className="text-sm text-gray-800 truncate">{uploadedFileName}</p>
                  <p className="text-xs text-gray-500">画像がアップロードされました</p>
                </div>
                <button
                  onClick={clearUploadedImage}
                  className="p-2 text-gray-500 hover:text-gray-700 hover:bg-gray-200 rounded"
                >
                  ✕
                </button>
              </div>
            ) : (
              <label
                htmlFor="image-upload"
                className="flex items-center justify-center gap-2 p-4 border-2 border-dashed border-gray-300 rounded-lg cursor-pointer hover:border-blue-500 hover:bg-blue-50 transition-colors"
              >
                <span className="text-2xl">📷</span>
                <span className="text-gray-600">画像をアップロード（クリックまたはドラッグ&ドロップ）</span>
              </label>
            )}
          </div>
        )}

        {/* Text Input */}
        <div className="flex gap-2">
          <textarea
            value={prompt}
            onChange={(e) => setPrompt(e.target.value)}
            placeholder={
              activeTab === 'analyze'
                ? '画像について質問してください（例：「この画像に写っているものは何ですか？」）'
                : activeTab === 'generate-image'
                ? '生成したい画像を説明してください（例：「夕焼けの海岸で走る白い馬」）'
                : '生成したい動画を説明してください（例：「宇宙船が星間を飛行する様子」）'
            }
            disabled={isLoading}
            className="flex-1 min-h-[60px] max-h-[120px] px-4 py-3 bg-gray-50 border border-gray-300 rounded-xl text-gray-900 placeholder-gray-500 resize-none focus:outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500"
            onKeyDown={(e) => {
              if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                handleSubmit();
              }
            }}
          />
          <button
            onClick={handleSubmit}
            disabled={isLoading || (!prompt.trim() && !uploadedImage)}
            className="self-end px-6 py-3 bg-blue-500 text-white font-medium rounded-xl hover:bg-blue-600 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            {isLoading ? (
              <div className="w-5 h-5 border-2 border-white border-t-transparent rounded-full animate-spin" />
            ) : activeTab === 'analyze' ? (
              '👁️ 解析'
            ) : activeTab === 'generate-image' ? (
              '🎨 生成'
            ) : (
              '🎬 生成'
            )}
          </button>
        </div>
        
        <p className="mt-2 text-xs text-gray-500">
          {activeTab === 'analyze'
            ? 'Nova Vision で画像を解析します。画像+質問、または画像のみ、質問のみでも動作します。'
            : activeTab === 'generate-image'
            ? 'Nova Canvas でテキストから画像を生成します。詳細な説明ほど良い結果が得られます。'
            : 'Nova Reel でテキストから動画を生成します。処理には数分かかる場合があります。'}
        </p>
      </div>
    </div>
  );
}
