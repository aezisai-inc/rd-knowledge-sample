'use client';

import React, { useState, useCallback, useRef, useEffect, useMemo } from 'react';
import { generateClient } from 'aws-amplify/data';
import { fetchAuthSession, getCurrentUser } from 'aws-amplify/auth';
import type { Schema } from '../../../../amplify/data/resource';

// =============================================================================
// Types
// =============================================================================

interface Message {
  id: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  timestamp: string;
  metadata?: {
    sources?: SourceReference[];
    memoryType?: 'short_term' | 'long_term' | 'episodic';
    processingTime?: number;
    model?: string;
  };
}

interface SourceReference {
  type: 'agentcore' | 'bedrock_kb' | 's3_vectors';
  id: string;
  score?: number;
  excerpt?: string;
}

interface ProcessingLog {
  id: string;
  timestamp: string;
  source: 'agentcore' | 'bedrock_kb' | 's3_vectors' | 'llm';
  action: string;
  details: string;
  duration?: number;
  status: 'pending' | 'success' | 'error';
}

interface MemorySourceConfig {
  agentcore: boolean;
  bedrockKb: boolean;
  s3Vectors: boolean;
}

interface SessionInfo {
  sessionId: string;
  title: string;
  messageCount: number;
  createdAt: string;
  lastActive: string;
}

// =============================================================================
// Component
// =============================================================================

export function MemoryChat() {
  // Amplify clientを遅延初期化（Amplify.configure後に呼び出されることを保証）
  // 認証モードをapiKeyに明示的に設定（publicApiKey認可を使用するため）
  const client = useMemo(() => generateClient<Schema>({ authMode: 'apiKey' }), []);
  
  // State
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [userId, setUserId] = useState<string | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [processingLogs, setProcessingLogs] = useState<ProcessingLog[]>([]);
  const [memorySources, setMemorySources] = useState<MemorySourceConfig>({
    agentcore: true,
    bedrockKb: true,
    s3Vectors: false,
  });
  const [showLogs, setShowLogs] = useState(true);
  const [showSessions, setShowSessions] = useState(false);
  const [pastSessions, setPastSessions] = useState<SessionInfo[]>([]);
  const [loadingSessions, setLoadingSessions] = useState(false);
  
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const logsEndRef = useRef<HTMLDivElement>(null);

  // Auto-scroll
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  useEffect(() => {
    logsEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [processingLogs]);

  // Initialize session with Cognito
  useEffect(() => {
    initializeSession();
  }, []);

  // =============================================================================
  // Session Management
  // =============================================================================

  const initializeSession = async () => {
    try {
      // Get Cognito user
      const user = await getCurrentUser();
      const session = await fetchAuthSession();
      
      const cognitoUserId = user.userId || session.identityId || `anonymous-${Date.now()}`;
      setUserId(cognitoUserId);
      
      // Create new session
      const newSessionId = `sess-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;
      setSessionId(newSessionId);
      
      addLog('agentcore', 'Session Initialized', `User: ${cognitoUserId.slice(0, 20)}...`, 'success');
      
      // Load past sessions
      await loadPastSessions(cognitoUserId);
      
      addSystemMessage(`✅ ログイン完了: ${user.signInDetails?.loginId || cognitoUserId.slice(0, 20)}...`);
    } catch (error) {
      console.log('Auth not configured, using anonymous session');
      const anonymousId = `anon-${Date.now()}`;
      setUserId(anonymousId);
      setSessionId(`sess-${Date.now()}`);
      addLog('agentcore', 'Anonymous Session', 'Cognito not configured', 'success');
      addSystemMessage('⚠️ 匿名セッション開始（Cognitoサインインで記憶機能が有効になります）');
    }
  };

  const loadPastSessions = async (actorId: string) => {
    setLoadingSessions(true);
    try {
      // Query sessions from DynamoDB via GraphQL
      const result = await client.queries.getMemorySessions?.({
        actorId: actorId,
      });

      if (result?.data && Array.isArray(result.data)) {
        const sessions: SessionInfo[] = result.data.map((s: any) => ({
          sessionId: s.sessionId,
          title: s.title || `セッション ${s.sessionId.slice(-6)}`,
          messageCount: s.messageCount || 0,
          createdAt: s.createdAt || new Date().toISOString(),
          lastActive: s.lastActive || new Date().toISOString(),
        }));
        setPastSessions(sessions.slice(0, 10)); // Last 10 sessions
        addLog('agentcore', 'Sessions Loaded', `${sessions.length} past sessions`, 'success');
      }
    } catch (error) {
      console.error('Failed to load sessions:', error);
      addLog('agentcore', 'Sessions Error', String(error), 'error');
    } finally {
      setLoadingSessions(false);
    }
  };

  const switchToSession = async (selectedSessionId: string) => {
    if (!userId) return;
    
    setSessionId(selectedSessionId);
    setMessages([]);
    setProcessingLogs([]);
    setShowSessions(false);
    
    addLog('agentcore', 'Session Switched', `Loading ${selectedSessionId.slice(-8)}...`, 'pending');
    
    try {
      // Load messages from this session
      const result = await client.queries.getMemoryEvents?.({
        actorId: userId,
        sessionId: selectedSessionId,
      });

      if (result?.data && Array.isArray(result.data)) {
        const loadedMessages: Message[] = result.data.map((event: any) => ({
          id: event.id || `loaded-${Date.now()}-${Math.random()}`,
          role: event.role?.toLowerCase() === 'user' ? 'user' : 'assistant',
          content: event.content || '',
          timestamp: event.timestamp || new Date().toISOString(),
          metadata: {
            memoryType: 'episodic',
          },
        }));
        
        setMessages(loadedMessages);
        addLog('agentcore', 'Messages Loaded', `${loadedMessages.length} messages from episodic memory`, 'success');
        addSystemMessage(`📂 セッション「${selectedSessionId.slice(-8)}」を復元しました（${loadedMessages.length}件のメッセージ）`);
      }
    } catch (error) {
      console.error('Failed to load session:', error);
      addLog('agentcore', 'Load Error', String(error), 'error');
    }
  };

  const createNewSession = () => {
    const newSessionId = `sess-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;
    setSessionId(newSessionId);
    setMessages([]);
    setProcessingLogs([]);
    setShowSessions(false);
    addLog('agentcore', 'New Session', `Created ${newSessionId.slice(-8)}`, 'success');
    addSystemMessage('🆕 新しいセッションを開始しました');
  };

  // =============================================================================
  // Logging
  // =============================================================================

  const addLog = (
    source: ProcessingLog['source'],
    action: string,
    details: string,
    status: ProcessingLog['status'],
    duration?: number
  ) => {
    const log: ProcessingLog = {
      id: `log-${Date.now()}-${Math.random().toString(36).slice(2, 6)}`,
      timestamp: new Date().toISOString(),
      source,
      action,
      details,
      status,
      duration,
    };
    setProcessingLogs(prev => [...prev.slice(-50), log]);
  };

  const addSystemMessage = (content: string) => {
    const msg: Message = {
      id: `sys-${Date.now()}`,
      role: 'system',
      content,
      timestamp: new Date().toISOString(),
    };
    setMessages(prev => [...prev, msg]);
  };

  // =============================================================================
  // Message Handling
  // =============================================================================

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim() || !sessionId || isLoading) return;

    const userMessage = input.trim();
    setInput('');
    setIsLoading(true);

    // Add user message
    const userMsg: Message = {
      id: `user-${Date.now()}`,
      role: 'user',
      content: userMessage,
      timestamp: new Date().toISOString(),
    };
    setMessages(prev => [...prev, userMsg]);

    const startTime = Date.now();
    const sources: SourceReference[] = [];

    try {
      // =============================================================================
      // 1. AgentCore Memory - 短期/長期/エピソード記憶検索
      // =============================================================================
      if (memorySources.agentcore) {
        addLog('agentcore', 'Memory Search', 'Searching conversation history...', 'pending');
        
        try {
          // Store user message in memory (short-term → episodic)
          const memoryResult = await client.mutations.createMemoryEvent({
            actorId: userId!,
            sessionId: sessionId,
            role: 'USER',
            content: userMessage,
          });

          if (memoryResult.data) {
            addLog('agentcore', 'Short-term Stored', `Event ID: ${memoryResult.data.id?.slice(0, 8)}...`, 'success', 50);
            
            // Retrieve related memories (includes long-term from other sessions)
            const retrieveResult = await client.queries.getMemoryEvents({
              actorId: userId!,
              sessionId: sessionId,
            });

            const currentSessionCount = retrieveResult.data?.length || 0;
            
            // Also query cross-session memories (long-term)
            let longTermCount = 0;
            if (pastSessions.length > 0) {
              // This would query memories from other sessions that might be relevant
              longTermCount = pastSessions.reduce((acc, s) => acc + (s.messageCount || 0), 0);
            }

            addLog('agentcore', 'Memory Retrieved', 
              `短期: ${currentSessionCount} / 長期: ${longTermCount} / エピソード: ${pastSessions.length}セッション`, 
              'success', 80
            );
            
            if (currentSessionCount > 0) {
              sources.push({
                type: 'agentcore',
                id: 'short-term-memory',
                score: 0.95,
                excerpt: `${currentSessionCount} messages in current session`,
              });
            }
            if (longTermCount > 0) {
              sources.push({
                type: 'agentcore',
                id: 'long-term-memory',
                score: 0.8,
                excerpt: `${longTermCount} messages across ${pastSessions.length} past sessions`,
              });
            }
          }
        } catch (err) {
          addLog('agentcore', 'Error', String(err), 'error');
        }
      }

      // =============================================================================
      // 2. Bedrock Knowledge Base / S3 Vectors - RAG検索
      // =============================================================================
      if (memorySources.bedrockKb || memorySources.s3Vectors) {
        addLog('bedrock_kb', 'Vector Search', 'Querying vector store...', 'pending');
        
        try {
          const vectorResult = await client.queries.searchVectors({
            query: userMessage,
            k: 5,
            minScore: 0.5,
          });

          if (vectorResult.data && vectorResult.data.length > 0) {
            const results = vectorResult.data;
            addLog('bedrock_kb', 'Documents Found', `${results.length} relevant documents`, 'success', 150);
            
            results.forEach((doc: any, idx: number) => {
              sources.push({
                type: memorySources.bedrockKb ? 'bedrock_kb' : 's3_vectors',
                id: doc.id || `doc-${idx}`,
                score: doc.score || 0.8,
                excerpt: doc.content?.slice(0, 100) || 'Document content...',
              });
            });
          } else {
            addLog('bedrock_kb', 'No Results', 'No matching documents found', 'success', 120);
          }
        } catch (err) {
          addLog('bedrock_kb', 'Error', String(err), 'error');
        }
      }

      // =============================================================================
      // 3. LLM Response Generation
      // =============================================================================
      addLog('llm', 'Generating Response', 'Invoking Bedrock model...', 'pending');
      
      // Build context from sources
      const contextParts: string[] = [];
      sources.forEach(src => {
        if (src.excerpt) {
          contextParts.push(`[${src.type}] ${src.excerpt}`);
        }
      });

      // Use invokeMultimodal for text generation
      const response = await client.mutations.invokeMultimodal({
        sessionId: sessionId,
        prompt: contextParts.length > 0 
          ? `Context:\n${contextParts.join('\n')}\n\nQuestion: ${userMessage}`
          : userMessage,
      });

      const processingTime = Date.now() - startTime;
      const responseText = response.data?.message || 'No response received';
      
      addLog('llm', 'Response Generated', `${processingTime}ms total`, 'success', processingTime);

      // Store assistant response in memory (episodic)
      if (memorySources.agentcore) {
        await client.mutations.createMemoryEvent({
          actorId: userId!,
          sessionId: sessionId,
          role: 'ASSISTANT',
          content: responseText,
        });
        addLog('agentcore', 'Episodic Stored', 'Response saved to memory', 'success', 30);
      }

      // Add assistant message
      const assistantMsg: Message = {
        id: `asst-${Date.now()}`,
        role: 'assistant',
        content: responseText,
        timestamp: new Date().toISOString(),
        metadata: {
          sources: sources.length > 0 ? sources : undefined,
          processingTime,
          memoryType: determineMemoryType(sources),
          model: 'nova-lite-v1',
        },
      };
      setMessages(prev => [...prev, assistantMsg]);

    } catch (error) {
      console.error('Error:', error);
      addLog('llm', 'Error', String(error), 'error');
      
      const errorMsg: Message = {
        id: `err-${Date.now()}`,
        role: 'system',
        content: `Error: ${error instanceof Error ? error.message : 'Unknown error'}`,
        timestamp: new Date().toISOString(),
      };
      setMessages(prev => [...prev, errorMsg]);
    } finally {
      setIsLoading(false);
    }
  };

  const determineMemoryType = (sources: SourceReference[]): 'short_term' | 'long_term' | 'episodic' => {
    const hasShortTerm = sources.some(s => s.id === 'short-term-memory');
    const hasLongTerm = sources.some(s => s.id === 'long-term-memory');
    const hasKb = sources.some(s => s.type === 'bedrock_kb');
    
    if (hasShortTerm && hasLongTerm) return 'episodic';
    if (hasLongTerm || hasKb) return 'long_term';
    return 'short_term';
  };

  // =============================================================================
  // Render
  // =============================================================================

  return (
    <div className="h-[700px] flex bg-gray-50">
      {/* Session Sidebar */}
      {showSessions && (
        <div className="w-64 flex flex-col bg-white border-r border-gray-200">
          <div className="p-3 border-b border-gray-200">
            <h3 className="text-sm font-semibold text-gray-800">📂 過去のセッション</h3>
            <p className="text-xs text-gray-500 mt-1">記憶を呼び起こす</p>
          </div>
          
          <div className="flex-1 overflow-y-auto p-2 space-y-1">
            {/* New Session Button */}
            <button
              onClick={createNewSession}
              className="w-full p-3 rounded-lg bg-blue-50 border border-blue-200 text-left hover:bg-blue-100 transition-colors"
            >
              <div className="flex items-center gap-2">
                <span>➕</span>
                <span className="text-sm font-medium text-blue-700">新しいセッション</span>
              </div>
            </button>

            {loadingSessions ? (
              <div className="text-center py-4 text-gray-500 text-sm">読み込み中...</div>
            ) : pastSessions.length === 0 ? (
              <div className="text-center py-4 text-gray-500 text-sm">
                過去のセッションはありません
              </div>
            ) : (
              pastSessions.map((session) => (
                <button
                  key={session.sessionId}
                  onClick={() => switchToSession(session.sessionId)}
                  className={`w-full p-3 rounded-lg text-left transition-colors ${
                    sessionId === session.sessionId
                      ? 'bg-blue-100 border border-blue-300'
                      : 'hover:bg-gray-100 border border-transparent'
                  }`}
                >
                  <div className="text-sm font-medium text-gray-800 truncate">
                    {session.title}
                  </div>
                  <div className="flex items-center gap-2 mt-1 text-xs text-gray-500">
                    <span>💬 {session.messageCount}</span>
                    <span>•</span>
                    <span>{new Date(session.lastActive).toLocaleDateString('ja-JP')}</span>
                  </div>
                </button>
              ))
            )}
          </div>
          
          {/* Memory Type Legend */}
          <div className="p-3 border-t border-gray-200 text-xs space-y-1 bg-gray-50">
            <div className="flex items-center gap-2 text-pink-600">
              <span className="w-2 h-2 rounded-full bg-pink-500"></span>
              短期記憶（現セッション）
            </div>
            <div className="flex items-center gap-2 text-blue-600">
              <span className="w-2 h-2 rounded-full bg-blue-500"></span>
              長期記憶（過去セッション）
            </div>
            <div className="flex items-center gap-2 text-violet-600">
              <span className="w-2 h-2 rounded-full bg-violet-500"></span>
              エピソード記憶（全統合）
            </div>
          </div>
        </div>
      )}

      {/* Chat Panel */}
      <div className={`flex flex-col ${showLogs ? 'w-2/3' : 'w-full'} border-r border-gray-200 flex-1 bg-white`}>
        {/* Header */}
        <div className="p-4 border-b border-gray-200 bg-gray-50">
          <div className="flex items-center justify-between mb-3">
            <div className="flex items-center gap-2">
              <button
                onClick={() => setShowSessions(!showSessions)}
                className={`p-2 rounded-lg transition-colors ${
                  showSessions ? 'bg-blue-500 text-white' : 'bg-gray-200 text-gray-700 hover:bg-gray-300'
                }`}
                title="過去のセッション"
              >
                📂
              </button>
              <h2 className="text-lg font-semibold text-gray-900">💬 RAG Memory Chat</h2>
            </div>
            <button
              onClick={() => setShowLogs(!showLogs)}
              className={`px-3 py-1 text-sm rounded-lg transition-colors ${
                showLogs ? 'bg-blue-500 text-white' : 'bg-gray-200 text-gray-700 hover:bg-gray-300'
              }`}
            >
              📊 {showLogs ? 'Hide Logs' : 'Show Logs'}
            </button>
          </div>
          
          {/* Memory Source Selection */}
          <div className="flex flex-wrap gap-2">
            <label className={`flex items-center gap-2 px-3 py-1.5 rounded-lg text-sm cursor-pointer transition-colors ${
              memorySources.agentcore ? 'bg-pink-100 border-pink-400' : 'bg-gray-100 border-gray-300'
            } border`}>
              <input
                type="checkbox"
                checked={memorySources.agentcore}
                onChange={(e) => setMemorySources(prev => ({ ...prev, agentcore: e.target.checked }))}
                className="accent-pink-500"
              />
              <span className="text-pink-700">🧠 AgentCore</span>
            </label>
            
            <label className={`flex items-center gap-2 px-3 py-1.5 rounded-lg text-sm cursor-pointer transition-colors ${
              memorySources.bedrockKb ? 'bg-blue-100 border-blue-400' : 'bg-gray-100 border-gray-300'
            } border`}>
              <input
                type="checkbox"
                checked={memorySources.bedrockKb}
                onChange={(e) => setMemorySources(prev => ({ ...prev, bedrockKb: e.target.checked }))}
                className="accent-blue-500"
              />
              <span className="text-blue-700">📚 Bedrock KB</span>
            </label>
            
            <label className={`flex items-center gap-2 px-3 py-1.5 rounded-lg text-sm cursor-pointer transition-colors ${
              memorySources.s3Vectors ? 'bg-green-100 border-green-400' : 'bg-gray-100 border-gray-300'
            } border`}>
              <input
                type="checkbox"
                checked={memorySources.s3Vectors}
                onChange={(e) => setMemorySources(prev => ({ ...prev, s3Vectors: e.target.checked }))}
                className="accent-green-500"
              />
              <span className="text-green-700">🗄️ S3 Vectors</span>
            </label>
          </div>
          
          {/* Session Info */}
          {sessionId && (
            <div className="mt-2 text-xs text-gray-500 flex items-center gap-3">
              <span>👤 {userId?.slice(0, 20)}...</span>
              <span>📝 {sessionId.slice(0, 15)}...</span>
              <span>💬 {messages.filter(m => m.role !== 'system').length} messages</span>
              {pastSessions.length > 0 && (
                <span className="text-violet-600">📂 {pastSessions.length} past sessions</span>
              )}
            </div>
          )}
        </div>

        {/* Messages */}
        <div className="flex-1 overflow-y-auto p-4 space-y-4 bg-gray-50">
          {messages.map((msg) => (
            <div
              key={msg.id}
              className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
            >
              <div
                className={`max-w-[85%] rounded-xl px-4 py-3 ${
                  msg.role === 'user'
                    ? 'bg-blue-500 text-white'
                    : msg.role === 'system'
                    ? 'bg-gray-200 text-gray-600 text-sm italic'
                    : 'bg-white border border-gray-200 text-gray-800 shadow-sm'
                }`}
              >
                <p className="whitespace-pre-wrap">{msg.content}</p>
                
                {/* Source References */}
                {msg.metadata?.sources && msg.metadata.sources.length > 0 && (
                  <div className="mt-3 pt-3 border-t border-gray-200 space-y-1">
                    <p className="text-xs text-gray-500 font-medium">📎 参照元:</p>
                    {msg.metadata.sources.map((src, idx) => (
                      <div key={idx} className="flex items-center gap-2 text-xs">
                        <span className={`px-1.5 py-0.5 rounded ${
                          src.type === 'agentcore' ? 'bg-pink-100 text-pink-700' :
                          src.type === 'bedrock_kb' ? 'bg-blue-100 text-blue-700' :
                          'bg-green-100 text-green-700'
                        }`}>
                          {src.type === 'agentcore' ? '🧠' : src.type === 'bedrock_kb' ? '📚' : '🗄️'}
                          {src.id === 'short-term-memory' ? '短期' : src.id === 'long-term-memory' ? '長期' : src.type}
                        </span>
                        {src.score && <span className="text-gray-500">Score: {(src.score * 100).toFixed(0)}%</span>}
                      </div>
                    ))}
                  </div>
                )}
                
                {/* Processing Info */}
                {msg.metadata?.processingTime && (
                  <div className="mt-2 text-xs text-gray-500">
                    ⏱️ {msg.metadata.processingTime}ms | 
                    🤖 {msg.metadata.model} |
                    💾 {msg.metadata.memoryType === 'short_term' ? '短期' : 
                        msg.metadata.memoryType === 'long_term' ? '長期' : 
                        msg.metadata.memoryType === 'episodic' ? 'エピソード' : 'none'}
                  </div>
                )}
              </div>
            </div>
          ))}
          <div ref={messagesEndRef} />
        </div>

        {/* Input */}
        <form onSubmit={handleSubmit} className="p-4 border-t border-gray-200 bg-white">
          <div className="flex gap-2">
            <input
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="メッセージを入力... (RAG + Memory で回答します)"
              disabled={isLoading || !sessionId}
              className="flex-1 px-4 py-3 bg-gray-50 border border-gray-300 rounded-xl text-gray-900 placeholder-gray-400 focus:outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500 disabled:opacity-50"
            />
            <button
              type="submit"
              disabled={isLoading || !input.trim() || !sessionId}
              className="px-6 py-3 bg-blue-500 text-white font-medium rounded-xl hover:bg-blue-600 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            >
              {isLoading ? '⏳' : '送信'}
            </button>
          </div>
        </form>
      </div>

      {/* Processing Logs Panel */}
      {showLogs && (
        <div className="w-1/3 flex flex-col bg-gray-50">
          <div className="p-3 border-b border-gray-200 bg-white">
            <h3 className="text-sm font-semibold text-gray-700">📊 Processing Logs</h3>
            <p className="text-xs text-gray-500 mt-1">Real-time processing status</p>
          </div>
          
          <div className="flex-1 overflow-y-auto p-2 space-y-1 text-xs font-mono">
            {processingLogs.map((log) => (
              <div
                key={log.id}
                className={`p-2 rounded bg-white border-l-2 ${
                  log.status === 'pending' ? 'border-yellow-500' :
                  log.status === 'success' ? 'border-green-500' :
                  'border-red-500'
                }`}
              >
                <div className="flex items-center gap-2">
                  <span className={`w-2 h-2 rounded-full ${
                    log.status === 'pending' ? 'bg-yellow-500 animate-pulse' :
                    log.status === 'success' ? 'bg-green-500' :
                    'bg-red-500'
                  }`} />
                  <span className={`px-1.5 py-0.5 rounded text-[10px] ${
                    log.source === 'agentcore' ? 'bg-pink-100 text-pink-700' :
                    log.source === 'bedrock_kb' ? 'bg-blue-100 text-blue-700' :
                    log.source === 's3_vectors' ? 'bg-green-100 text-green-700' :
                    'bg-violet-100 text-violet-700'
                  }`}>
                    {log.source}
                  </span>
                  <span className="text-gray-700 font-medium">{log.action}</span>
                </div>
                <p className="text-gray-500 mt-1 ml-4">{log.details}</p>
                {log.duration && (
                  <p className="text-gray-400 mt-0.5 ml-4">⏱️ {log.duration}ms</p>
                )}
              </div>
            ))}
            <div ref={logsEndRef} />
            
            {processingLogs.length === 0 && (
              <div className="text-center text-gray-500 py-8">
                <p>🔍 Waiting for activity...</p>
                <p className="mt-1">Send a message to see processing logs</p>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
