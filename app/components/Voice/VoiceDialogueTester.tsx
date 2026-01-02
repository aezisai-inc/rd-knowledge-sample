"use client";

import { useState, useRef, useEffect, useCallback } from "react";

interface VoiceDialogueTesterProps {
  apiBaseUrl: string;
}

interface ConversationEntry {
  id: string;
  role: "user" | "assistant";
  text: string;
  timestamp: Date;
}

type ConnectionStatus = "disconnected" | "connecting" | "connected" | "error";

export function VoiceDialogueTester({ apiBaseUrl }: VoiceDialogueTesterProps) {
  const [isRecording, setIsRecording] = useState(false);
  const [connectionStatus, setConnectionStatus] = useState<ConnectionStatus>("disconnected");
  const [conversation, setConversation] = useState<ConversationEntry[]>([]);
  const [currentTranscript, setCurrentTranscript] = useState("");
  const [voiceId, setVoiceId] = useState("ruth");
  const [language, setLanguage] = useState("en-US");
  const [audioLevel, setAudioLevel] = useState(0);

  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const audioContextRef = useRef<AudioContext | null>(null);
  const analyserRef = useRef<AnalyserNode | null>(null);
  const animationFrameRef = useRef<number | null>(null);
  const audioQueueRef = useRef<AudioBuffer[]>([]);
  const conversationEndRef = useRef<HTMLDivElement>(null);

  // Scroll to bottom when conversation updates
  useEffect(() => {
    conversationEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [conversation]);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (animationFrameRef.current) {
        cancelAnimationFrame(animationFrameRef.current);
      }
      if (audioContextRef.current) {
        audioContextRef.current.close();
      }
    };
  }, []);

  const updateAudioLevel = useCallback(() => {
    if (analyserRef.current) {
      const dataArray = new Uint8Array(analyserRef.current.frequencyBinCount);
      analyserRef.current.getByteFrequencyData(dataArray);
      const average = dataArray.reduce((a, b) => a + b) / dataArray.length;
      setAudioLevel(average / 255);
    }
    animationFrameRef.current = requestAnimationFrame(updateAudioLevel);
  }, []);

  const startRecording = async () => {
    try {
      setConnectionStatus("connecting");

      // Get microphone access
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: {
          sampleRate: 16000,
          channelCount: 1,
          echoCancellation: true,
          noiseSuppression: true,
        },
      });

      // Setup audio analysis
      audioContextRef.current = new AudioContext({ sampleRate: 16000 });
      const source = audioContextRef.current.createMediaStreamSource(stream);
      analyserRef.current = audioContextRef.current.createAnalyser();
      analyserRef.current.fftSize = 256;
      source.connect(analyserRef.current);

      // Start level monitoring
      updateAudioLevel();

      // Setup MediaRecorder
      mediaRecorderRef.current = new MediaRecorder(stream, {
        mimeType: "audio/webm;codecs=opus",
      });

      mediaRecorderRef.current.ondataavailable = async (event) => {
        if (event.data.size > 0) {
          // Convert to base64 and send to API
          const reader = new FileReader();
          reader.onload = async () => {
            const base64 = (reader.result as string).split(",")[1];
            await sendAudioChunk(base64);
          };
          reader.readAsDataURL(event.data);
        }
      };

      mediaRecorderRef.current.start(1000); // Send chunks every second
      setIsRecording(true);
      setConnectionStatus("connected");

      // Add placeholder for user input
      setCurrentTranscript("Listening...");

    } catch (error) {
      console.error("Failed to start recording:", error);
      setConnectionStatus("error");
    }
  };

  const stopRecording = () => {
    if (mediaRecorderRef.current && isRecording) {
      mediaRecorderRef.current.stop();
      mediaRecorderRef.current.stream.getTracks().forEach((track) => track.stop());
    }

    if (animationFrameRef.current) {
      cancelAnimationFrame(animationFrameRef.current);
    }

    setIsRecording(false);
    setConnectionStatus("disconnected");
    setAudioLevel(0);
    setCurrentTranscript("");
  };

  const sendAudioChunk = async (base64Audio: string) => {
    try {
      const response = await fetch(`${apiBaseUrl}/v1/agent/voice/process`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          audio: base64Audio,
          voice_id: voiceId,
          language: language,
        }),
      });

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }

      const data = await response.json();

      // Update transcript
      if (data.transcript) {
        setCurrentTranscript(data.transcript);
      }

      // Add to conversation
      if (data.user_text) {
        addConversationEntry("user", data.user_text);
      }
      if (data.assistant_text) {
        addConversationEntry("assistant", data.assistant_text);
      }

      // Play audio response
      if (data.audio) {
        await playAudioResponse(data.audio);
      }

    } catch (error) {
      console.error("Failed to send audio:", error);
    }
  };

  const addConversationEntry = (role: "user" | "assistant", text: string) => {
    setConversation((prev) => [
      ...prev,
      {
        id: `${Date.now()}-${Math.random()}`,
        role,
        text,
        timestamp: new Date(),
      },
    ]);
  };

  const playAudioResponse = async (base64Audio: string) => {
    try {
      if (!audioContextRef.current) {
        audioContextRef.current = new AudioContext();
      }

      const audioData = atob(base64Audio);
      const arrayBuffer = new ArrayBuffer(audioData.length);
      const view = new Uint8Array(arrayBuffer);
      for (let i = 0; i < audioData.length; i++) {
        view[i] = audioData.charCodeAt(i);
      }

      const audioBuffer = await audioContextRef.current.decodeAudioData(arrayBuffer);
      const source = audioContextRef.current.createBufferSource();
      source.buffer = audioBuffer;
      source.connect(audioContextRef.current.destination);
      source.start();

    } catch (error) {
      console.error("Failed to play audio:", error);
    }
  };

  const sendTextMessage = async (text: string) => {
    if (!text.trim()) return;

    addConversationEntry("user", text);

    try {
      const response = await fetch(`${apiBaseUrl}/v1/agent/voice/text`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          text,
          voice_id: voiceId,
          language: language,
        }),
      });

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }

      const data = await response.json();

      if (data.response) {
        addConversationEntry("assistant", data.response);
      }

      if (data.audio) {
        await playAudioResponse(data.audio);
      }

    } catch (error) {
      console.error("Failed to send text:", error);
      addConversationEntry("assistant", "申し訳ありません、エラーが発生しました。");
    }
  };

  const voices = [
    { id: "ruth", name: "Ruth (Female, US)" },
    { id: "matthew", name: "Matthew (Male, US)" },
    { id: "tiffany", name: "Tiffany (Female, US)" },
    { id: "amy", name: "Amy (Female, UK)" },
  ];

  const languages = [
    { code: "en-US", name: "English (US)" },
    { code: "en-GB", name: "English (UK)" },
    { code: "es-ES", name: "Spanish" },
    { code: "fr-FR", name: "French" },
    { code: "de-DE", name: "German" },
  ];

  const getStatusColor = () => {
    switch (connectionStatus) {
      case "connected": return "bg-green-500";
      case "connecting": return "bg-yellow-500 animate-pulse";
      case "error": return "bg-red-500";
      default: return "bg-slate-500";
    }
  };

  return (
    <div className="bg-gradient-to-br from-slate-800/80 to-slate-900/80 rounded-2xl p-6 border border-slate-700/50 shadow-xl">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-green-500 to-teal-500 flex items-center justify-center text-xl">
            🎙️
          </div>
          <div>
            <h2 className="text-xl font-bold text-white">Voice Dialogue</h2>
            <p className="text-sm text-slate-400">Nova 2 Sonic</p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <div className={`w-3 h-3 rounded-full ${getStatusColor()}`} />
          <span className="text-sm text-slate-400 capitalize">{connectionStatus}</span>
        </div>
      </div>

      {/* Audio Visualizer */}
      <div className="bg-slate-700/30 rounded-xl p-4 mb-6">
        <div className="flex items-center justify-center h-16 gap-1">
          {Array.from({ length: 20 }).map((_, i) => (
            <div
              key={i}
              className="w-2 bg-gradient-to-t from-green-500 to-teal-400 rounded-full transition-all duration-75"
              style={{
                height: `${Math.max(8, audioLevel * 64 * Math.sin((i / 20) * Math.PI))}px`,
              }}
            />
          ))}
        </div>
        {currentTranscript && (
          <p className="text-center text-sm text-slate-400 mt-2 italic">
            {currentTranscript}
          </p>
        )}
      </div>

      {/* Conversation Log */}
      <div className="bg-slate-700/30 rounded-xl p-4 mb-6 h-64 overflow-y-auto">
        {conversation.length === 0 ? (
          <div className="flex items-center justify-center h-full text-slate-500">
            <p>会話を開始してください</p>
          </div>
        ) : (
          <div className="space-y-3">
            {conversation.map((entry) => (
              <div
                key={entry.id}
                className={`flex ${entry.role === "user" ? "justify-end" : "justify-start"}`}
              >
                <div
                  className={`max-w-[80%] px-4 py-2 rounded-2xl ${
                    entry.role === "user"
                      ? "bg-green-500/20 text-green-100"
                      : "bg-slate-600/50 text-slate-200"
                  }`}
                >
                  <div className="flex items-center gap-2 mb-1">
                    <span>{entry.role === "user" ? "🧑" : "🤖"}</span>
                    <span className="text-xs text-slate-400">
                      {entry.timestamp.toLocaleTimeString()}
                    </span>
                  </div>
                  <p className="text-sm">{entry.text}</p>
                </div>
              </div>
            ))}
            <div ref={conversationEndRef} />
          </div>
        )}
      </div>

      {/* Controls */}
      <div className="flex gap-3 mb-6">
        <button
          onClick={isRecording ? stopRecording : startRecording}
          className={`flex-1 py-4 rounded-xl font-semibold transition-all ${
            isRecording
              ? "bg-red-500 hover:bg-red-600 animate-pulse"
              : "bg-gradient-to-r from-green-500 to-teal-500 hover:from-green-600 hover:to-teal-600"
          } text-white`}
        >
          {isRecording ? (
            <span className="flex items-center justify-center gap-2">
              <span className="w-4 h-4 bg-white rounded-sm" />
              録音停止
            </span>
          ) : (
            <span className="flex items-center justify-center gap-2">
              🎤 録音開始
            </span>
          )}
        </button>
      </div>

      {/* Text Input (Alternative) */}
      <div className="mb-6">
        <div className="flex gap-2">
          <input
            type="text"
            placeholder="テキストで入力..."
            className="flex-1 px-4 py-3 rounded-xl bg-slate-700/50 border border-slate-600 text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-green-500"
            onKeyDown={(e) => {
              if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault();
                sendTextMessage((e.target as HTMLInputElement).value);
                (e.target as HTMLInputElement).value = "";
              }
            }}
          />
          <button
            onClick={(e) => {
              const input = e.currentTarget.previousElementSibling as HTMLInputElement;
              sendTextMessage(input.value);
              input.value = "";
            }}
            className="px-4 py-3 rounded-xl bg-slate-600 hover:bg-slate-500 text-white transition-colors"
          >
            送信
          </button>
        </div>
      </div>

      {/* Settings */}
      <div className="grid grid-cols-2 gap-4">
        <div>
          <label className="block text-sm font-medium text-slate-400 mb-2">
            音声
          </label>
          <select
            value={voiceId}
            onChange={(e) => setVoiceId(e.target.value)}
            className="w-full px-3 py-2 rounded-lg bg-slate-700/50 border border-slate-600 text-white focus:outline-none focus:ring-2 focus:ring-green-500"
          >
            {voices.map((voice) => (
              <option key={voice.id} value={voice.id}>
                {voice.name}
              </option>
            ))}
          </select>
        </div>
        <div>
          <label className="block text-sm font-medium text-slate-400 mb-2">
            言語
          </label>
          <select
            value={language}
            onChange={(e) => setLanguage(e.target.value)}
            className="w-full px-3 py-2 rounded-lg bg-slate-700/50 border border-slate-600 text-white focus:outline-none focus:ring-2 focus:ring-green-500"
          >
            {languages.map((lang) => (
              <option key={lang.code} value={lang.code}>
                {lang.name}
              </option>
            ))}
          </select>
        </div>
      </div>

      {/* Info */}
      <div className="mt-6 p-4 bg-slate-700/30 rounded-xl">
        <h3 className="text-sm font-medium text-slate-300 mb-2">💡 使い方</h3>
        <ul className="text-xs text-slate-400 space-y-1">
          <li>• 「録音開始」をクリックしてマイクを有効化</li>
          <li>• 話しかけると AI が音声で応答します</li>
          <li>• テキスト入力も可能です</li>
          <li>• Nova 2 Sonic による自然な会話を体験してください</li>
        </ul>
      </div>
    </div>
  );
}

