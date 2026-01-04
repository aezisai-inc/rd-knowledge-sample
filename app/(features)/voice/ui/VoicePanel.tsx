'use client';

import React, { useState, useCallback, useRef, useEffect } from 'react';
import { generateClient } from 'aws-amplify/data';
import type { Schema } from '../../../amplify/data/resource';

const client = generateClient<Schema>();

interface Message {
  id: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  timestamp: string;
  audio?: string; // base64 audio
  isPlaying?: boolean;
}

type VoiceMode = 'text-to-speech' | 'speech-to-text' | 'dialogue';

export function VoicePanel() {
  const [sessionId] = useState(() => `voice-${Date.now()}`);
  const [messages, setMessages] = useState<Message[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [textInput, setTextInput] = useState('');
  const [voiceMode, setVoiceMode] = useState<VoiceMode>('dialogue');
  
  // Recording state
  const [isRecording, setIsRecording] = useState(false);
  const [recordingTime, setRecordingTime] = useState(0);
  const [audioBlob, setAudioBlob] = useState<Blob | null>(null);
  const [audioUrl, setAudioUrl] = useState<string | null>(null);
  
  // Refs
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const audioChunksRef = useRef<Blob[]>([]);
  const recordingTimerRef = useRef<NodeJS.Timeout | null>(null);
  const audioPlayerRef = useRef<HTMLAudioElement | null>(null);

  // =============================================================================
  // Recording Functions
  // =============================================================================

  const startRecording = useCallback(async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const mediaRecorder = new MediaRecorder(stream, {
        mimeType: 'audio/webm;codecs=opus',
      });
      
      mediaRecorderRef.current = mediaRecorder;
      audioChunksRef.current = [];
      
      mediaRecorder.ondataavailable = (event) => {
        if (event.data.size > 0) {
          audioChunksRef.current.push(event.data);
        }
      };
      
      mediaRecorder.onstop = () => {
        const blob = new Blob(audioChunksRef.current, { type: 'audio/webm' });
        setAudioBlob(blob);
        setAudioUrl(URL.createObjectURL(blob));
        
        // Stop all tracks
        stream.getTracks().forEach(track => track.stop());
      };
      
      mediaRecorder.start(100); // Collect data every 100ms
      setIsRecording(true);
      setRecordingTime(0);
      
      // Start timer
      recordingTimerRef.current = setInterval(() => {
        setRecordingTime(prev => prev + 1);
      }, 1000);
      
    } catch (error) {
      console.error('Failed to start recording:', error);
      addSystemMessage('⚠️ マイクへのアクセスが拒否されました。ブラウザの設定を確認してください。');
    }
  }, []);

  const stopRecording = useCallback(() => {
    if (mediaRecorderRef.current && isRecording) {
      mediaRecorderRef.current.stop();
      setIsRecording(false);
      
      if (recordingTimerRef.current) {
        clearInterval(recordingTimerRef.current);
        recordingTimerRef.current = null;
      }
    }
  }, [isRecording]);

  const clearRecording = useCallback(() => {
    setAudioBlob(null);
    if (audioUrl) {
      URL.revokeObjectURL(audioUrl);
    }
    setAudioUrl(null);
    setRecordingTime(0);
  }, [audioUrl]);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (recordingTimerRef.current) {
        clearInterval(recordingTimerRef.current);
      }
      if (audioUrl) {
        URL.revokeObjectURL(audioUrl);
      }
    };
  }, [audioUrl]);

  // =============================================================================
  // Message Handling
  // =============================================================================

  const addSystemMessage = (content: string) => {
    const msg: Message = {
      id: `sys-${Date.now()}`,
      role: 'system',
      content,
      timestamp: new Date().toISOString(),
    };
    setMessages(prev => [...prev, msg]);
  };

  const handleSendText = useCallback(async () => {
    if (!textInput.trim() || isLoading) return;

    const userMessage: Message = {
      id: `user-${Date.now()}`,
      role: 'user',
      content: textInput,
      timestamp: new Date().toISOString(),
    };

    setMessages(prev => [...prev, userMessage]);
    const currentText = textInput;
    setTextInput('');
    setIsLoading(true);

    try {
      // Call voice API for text-to-speech / dialogue
      const response = await client.mutations.invokeVoiceAgent?.({
        sessionId,
        text: currentText,
        mode: voiceMode === 'text-to-speech' ? 'TTS' : 'DIALOGUE',
      });

      const assistantMessage: Message = {
        id: `assistant-${Date.now()}`,
        role: 'assistant',
        content: response?.data?.text || 'No response',
        timestamp: new Date().toISOString(),
        audio: response?.data?.audio || undefined,
      };

      setMessages(prev => [...prev, assistantMessage]);
    } catch (error) {
      console.error('Voice request failed:', error);
      const errorMessage: Message = {
        id: `error-${Date.now()}`,
        role: 'system',
        content: `Error: ${error instanceof Error ? error.message : 'Unknown error'}`,
        timestamp: new Date().toISOString(),
      };
      setMessages(prev => [...prev, errorMessage]);
    } finally {
      setIsLoading(false);
    }
  }, [textInput, sessionId, isLoading, voiceMode]);

  const handleSendAudio = useCallback(async () => {
    if (!audioBlob || isLoading) return;

    // Convert blob to base64
    const reader = new FileReader();
    reader.onload = async () => {
      const base64Audio = (reader.result as string).split(',')[1];
      
      const userMessage: Message = {
        id: `user-${Date.now()}`,
        role: 'user',
        content: '🎤 音声メッセージ',
        timestamp: new Date().toISOString(),
        audio: base64Audio,
      };

      setMessages(prev => [...prev, userMessage]);
      clearRecording();
      setIsLoading(true);

      try {
        // Call voice API for speech-to-text / dialogue
        const response = await client.mutations.invokeVoiceAgent?.({
          sessionId,
          audio: base64Audio,
          mode: voiceMode === 'speech-to-text' ? 'STT' : 'DIALOGUE',
        });

        // Add transcription message if available
        if (response?.data?.transcription) {
          const transcriptionMessage: Message = {
            id: `transcription-${Date.now()}`,
            role: 'system',
            content: `📝 文字起こし: "${response.data.transcription}"`,
            timestamp: new Date().toISOString(),
          };
          setMessages(prev => [...prev, transcriptionMessage]);
        }

        // Add assistant response
        if (response?.data?.text || response?.data?.audio) {
          const assistantMessage: Message = {
            id: `assistant-${Date.now()}`,
            role: 'assistant',
            content: response.data.text || '音声応答',
            timestamp: new Date().toISOString(),
            audio: response.data.audio || undefined,
          };
          setMessages(prev => [...prev, assistantMessage]);
        }
      } catch (error) {
        console.error('Voice request failed:', error);
        const errorMessage: Message = {
          id: `error-${Date.now()}`,
          role: 'system',
          content: `Error: ${error instanceof Error ? error.message : 'Unknown error'}`,
          timestamp: new Date().toISOString(),
        };
        setMessages(prev => [...prev, errorMessage]);
      } finally {
        setIsLoading(false);
      }
    };
    reader.readAsDataURL(audioBlob);
  }, [audioBlob, sessionId, isLoading, voiceMode, clearRecording]);

  const playAudio = useCallback((base64Audio: string, messageId: string) => {
    if (audioPlayerRef.current) {
      audioPlayerRef.current.pause();
    }

    const audio = new Audio(`data:audio/mp3;base64,${base64Audio}`);
    audioPlayerRef.current = audio;

    setMessages(prev => prev.map(m => 
      m.id === messageId ? { ...m, isPlaying: true } : { ...m, isPlaying: false }
    ));

    audio.onended = () => {
      setMessages(prev => prev.map(m => ({ ...m, isPlaying: false })));
    };

    audio.play().catch(console.error);
  }, []);

  const formatTime = (seconds: number) => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  };

  // =============================================================================
  // Render
  // =============================================================================

  const modes: { id: VoiceMode; label: string; icon: string; description: string }[] = [
    { id: 'dialogue', label: '対話', icon: '💬', description: '音声入出力による対話' },
    { id: 'text-to-speech', label: '音声合成', icon: '🔊', description: 'テキスト→音声' },
    { id: 'speech-to-text', label: '文字起こし', icon: '📝', description: '音声→テキスト' },
  ];

  return (
    <div className="h-full flex flex-col">
      {/* Header */}
      <div className="p-4 border-b border-gray-700">
        <h2 className="text-lg font-semibold text-white flex items-center gap-2">
          <span>🎙️</span> Voice Dialogue
        </h2>
        <p className="text-sm text-gray-400">
          Nova Sonic - 音声対話AI
        </p>
        
        {/* Mode Selection */}
        <div className="flex gap-2 mt-3">
          {modes.map((mode) => (
            <button
              key={mode.id}
              onClick={() => setVoiceMode(mode.id)}
              className={`flex-1 px-3 py-2 rounded-lg text-sm font-medium transition-colors ${
                voiceMode === mode.id
                  ? 'bg-gradient-to-r from-green-500 to-teal-500 text-white'
                  : 'bg-gray-700 text-gray-400 hover:text-white'
              }`}
            >
              <span className="mr-1">{mode.icon}</span>
              {mode.label}
            </button>
          ))}
        </div>
      </div>

      {/* Messages Area */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {messages.length === 0 ? (
          <div className="h-full flex flex-col items-center justify-center text-gray-500">
            <p className="text-4xl mb-4">🎙️</p>
            <p className="text-lg font-medium">音声対話を始めましょう</p>
            <p className="text-sm mt-2 text-center">
              {voiceMode === 'dialogue' 
                ? 'マイクボタンで録音するか、テキストで入力してください'
                : voiceMode === 'text-to-speech'
                ? 'テキストを入力すると音声に変換されます'
                : 'マイクボタンで録音すると文字起こしされます'}
            </p>
          </div>
        ) : (
          messages.map((message) => (
            <div
              key={message.id}
              className={`flex ${message.role === 'user' ? 'justify-end' : message.role === 'system' ? 'justify-center' : 'justify-start'}`}
            >
              <div
                className={`max-w-[80%] rounded-xl p-4 ${
                  message.role === 'user'
                    ? 'bg-gradient-to-r from-green-500 to-teal-500 text-white'
                    : message.role === 'system'
                    ? 'bg-gray-700/50 text-gray-400 text-sm italic'
                    : 'bg-gray-700 text-gray-100'
                }`}
              >
                <p className="whitespace-pre-wrap">{message.content}</p>
                
                {/* Audio Player */}
                {message.audio && message.role !== 'user' && (
                  <button
                    onClick={() => playAudio(message.audio!, message.id)}
                    className={`mt-3 px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
                      message.isPlaying
                        ? 'bg-green-500/30 text-green-300'
                        : 'bg-gray-600 text-white hover:bg-gray-500'
                    }`}
                  >
                    {message.isPlaying ? '🔊 再生中...' : '▶️ 音声を再生'}
                  </button>
                )}
                
                <p className="text-xs text-gray-400 mt-2">
                  {new Date(message.timestamp).toLocaleTimeString()}
                </p>
              </div>
            </div>
          ))
        )}
        {isLoading && (
          <div className="flex items-center gap-2 text-gray-400 justify-center py-4">
            <div className="w-5 h-5 border-2 border-green-500 border-t-transparent rounded-full animate-spin" />
            <span className="text-sm">処理中...</span>
          </div>
        )}
      </div>

      {/* Input Area */}
      <div className="border-t border-gray-700 p-4 space-y-3">
        {/* Recording Controls */}
        <div className="flex items-center justify-center gap-4">
          {!isRecording && !audioBlob ? (
            <button
              onClick={startRecording}
              disabled={isLoading}
              className="w-16 h-16 rounded-full bg-gradient-to-r from-red-500 to-pink-500 text-white text-2xl flex items-center justify-center hover:scale-105 transition-transform disabled:opacity-50 disabled:cursor-not-allowed shadow-lg"
              title="録音開始"
            >
              🎤
            </button>
          ) : isRecording ? (
            <div className="flex items-center gap-4">
              <div className="text-center">
                <p className="text-red-400 text-sm animate-pulse">● 録音中</p>
                <p className="text-white font-mono">{formatTime(recordingTime)}</p>
              </div>
              <button
                onClick={stopRecording}
                className="w-16 h-16 rounded-full bg-red-500 text-white text-2xl flex items-center justify-center hover:scale-105 transition-transform shadow-lg"
                title="録音停止"
              >
                ⬛
              </button>
            </div>
          ) : audioBlob ? (
            <div className="flex items-center gap-4">
              <audio src={audioUrl || undefined} controls className="h-10" />
              <button
                onClick={clearRecording}
                className="p-2 text-gray-400 hover:text-white hover:bg-gray-700 rounded-lg"
                title="録音を削除"
              >
                🗑️
              </button>
              <button
                onClick={handleSendAudio}
                disabled={isLoading}
                className="px-4 py-2 bg-gradient-to-r from-green-500 to-teal-500 text-white rounded-lg hover:opacity-90 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                📤 送信
              </button>
            </div>
          ) : null}
        </div>

        <div className="relative">
          <div className="absolute inset-0 flex items-center">
            <div className="w-full border-t border-gray-700"></div>
          </div>
          <div className="relative flex justify-center text-sm">
            <span className="px-2 bg-gray-800 text-gray-500">または</span>
          </div>
        </div>

        {/* Text Input */}
        <div className="flex gap-2">
          <input
            type="text"
            value={textInput}
            onChange={(e) => setTextInput(e.target.value)}
            placeholder={
              voiceMode === 'speech-to-text'
                ? '音声を録音してください...'
                : 'テキストを入力...'
            }
            disabled={isLoading || voiceMode === 'speech-to-text'}
            className="flex-1 px-4 py-3 bg-gray-700 border border-gray-600 rounded-xl text-white placeholder-gray-500 focus:outline-none focus:border-green-500 disabled:opacity-50"
            onKeyDown={(e) => {
              if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                handleSendText();
              }
            }}
          />
          <button
            onClick={handleSendText}
            disabled={isLoading || !textInput.trim() || voiceMode === 'speech-to-text'}
            className="px-6 py-3 bg-gradient-to-r from-green-500 to-teal-500 text-white font-medium rounded-xl hover:opacity-90 disabled:opacity-50 disabled:cursor-not-allowed transition-opacity"
          >
            {isLoading ? '⏳' : '送信'}
          </button>
        </div>
        
        <p className="text-xs text-gray-500 text-center">
          {voiceMode === 'dialogue'
            ? 'Nova Sonic で音声対話します。音声または テキストで入力できます。'
            : voiceMode === 'text-to-speech'
            ? 'テキストを音声に変換します（TTS）'
            : '音声を文字に変換します（STT）'}
        </p>
      </div>
    </div>
  );
}
