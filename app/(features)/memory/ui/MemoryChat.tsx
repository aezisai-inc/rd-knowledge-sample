'use client';

import React, { useState, useCallback, useRef, useEffect } from 'react';
import { generateClient } from 'aws-amplify/data';
import { fetchAuthSession, getCurrentUser } from 'aws-amplify/auth';
import type { Schema } from '../../../../amplify/data/resource';

const client = generateClient<Schema>();

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

// =============================================================================
// Component
// =============================================================================

export function MemoryChat() {
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
      
      addSystemMessage(`Session started. User ID: ${cognitoUserId.slice(0, 20)}...`);
    } catch (error) {
      console.log('Auth not configured, using anonymous session');
      const anonymousId = `anon-${Date.now()}`;
      setUserId(anonymousId);
      setSessionId(`sess-${Date.now()}`);
      addLog('agentcore', 'Anonymous Session', 'Cognito not configured', 'success');
      addSystemMessage('Anonymous session started (Cognito not configured)');
    }
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
    setProcessingLogs(prev => [...prev.slice(-50), log]); // Keep last 50 logs
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
          // Store user message in memory
          const memoryResult = await client.mutations.createMemoryEvent({
            actorId: userId!,
            sessionId: sessionId,
            role: 'USER',
            content: userMessage,
          });

          if (memoryResult.data) {
            addLog('agentcore', 'Event Stored', `ID: ${memoryResult.data.id?.slice(0, 8)}...`, 'success', 50);
            
            // Retrieve related memories
            const retrieveResult = await client.queries.getMemoryEvents({
              actorId: userId!,
              sessionId: sessionId,
            });

            const memoryCount = retrieveResult.data?.length || 0;
            addLog('agentcore', 'Memory Retrieved', `Found ${memoryCount} related memories`, 'success', 80);
            
            if (memoryCount > 0) {
              sources.push({
                type: 'agentcore',
                id: 'conversation-history',
                score: 0.95,
                excerpt: `${memoryCount} previous messages in session`,
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
      // 3. LLM Response Generation (via Multimodal Agent)
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

      // Store assistant response in memory
      if (memorySources.agentcore) {
        await client.mutations.createMemoryEvent({
          actorId: userId!,
          sessionId: sessionId,
          role: 'ASSISTANT',
          content: responseText,
        });
        addLog('agentcore', 'Response Stored', 'Added to episodic memory', 'success', 30);
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

  const determineMemoryType = (sources: SourceReference[]): Message['metadata']['memoryType'] => {
    const hasAgentCore = sources.some(s => s.type === 'agentcore');
    const hasKb = sources.some(s => s.type === 'bedrock_kb');
    
    if (hasAgentCore && hasKb) return 'episodic';
    if (hasAgentCore) return 'short_term';
    return 'long_term';
  };

  // =============================================================================
  // Render
  // =============================================================================

  return (
    <div className="h-[700px] flex">
      {/* Chat Panel */}
      <div className={`flex flex-col ${showLogs ? 'w-2/3' : 'w-full'} border-r border-slate-700`}>
        {/* Header */}
        <div className="p-4 border-b border-slate-700 bg-slate-800/50">
          <div className="flex items-center justify-between mb-3">
            <h2 className="text-lg font-semibold text-white">💬 RAG Memory Chat</h2>
            <button
              onClick={() => setShowLogs(!showLogs)}
              className={`px-3 py-1 text-sm rounded-lg transition-colors ${
                showLogs ? 'bg-violet-500 text-white' : 'bg-slate-700 text-slate-300'
              }`}
            >
              📊 {showLogs ? 'Hide Logs' : 'Show Logs'}
            </button>
          </div>
          
          {/* Memory Source Selection */}
          <div className="flex flex-wrap gap-2">
            <label className={`flex items-center gap-2 px-3 py-1.5 rounded-lg text-sm cursor-pointer transition-colors ${
              memorySources.agentcore ? 'bg-pink-500/20 border-pink-500/50' : 'bg-slate-700/50 border-slate-600'
            } border`}>
              <input
                type="checkbox"
                checked={memorySources.agentcore}
                onChange={(e) => setMemorySources(prev => ({ ...prev, agentcore: e.target.checked }))}
                className="accent-pink-500"
              />
              <span className="text-pink-300">🧠 AgentCore</span>
            </label>
            
            <label className={`flex items-center gap-2 px-3 py-1.5 rounded-lg text-sm cursor-pointer transition-colors ${
              memorySources.bedrockKb ? 'bg-blue-500/20 border-blue-500/50' : 'bg-slate-700/50 border-slate-600'
            } border`}>
              <input
                type="checkbox"
                checked={memorySources.bedrockKb}
                onChange={(e) => setMemorySources(prev => ({ ...prev, bedrockKb: e.target.checked }))}
                className="accent-blue-500"
              />
              <span className="text-blue-300">📚 Bedrock KB</span>
            </label>
            
            <label className={`flex items-center gap-2 px-3 py-1.5 rounded-lg text-sm cursor-pointer transition-colors ${
              memorySources.s3Vectors ? 'bg-green-500/20 border-green-500/50' : 'bg-slate-700/50 border-slate-600'
            } border`}>
              <input
                type="checkbox"
                checked={memorySources.s3Vectors}
                onChange={(e) => setMemorySources(prev => ({ ...prev, s3Vectors: e.target.checked }))}
                className="accent-green-500"
              />
              <span className="text-green-300">🗄️ S3 Vectors</span>
            </label>
          </div>
          
          {/* Session Info */}
          {sessionId && (
            <div className="mt-2 text-xs text-slate-400">
              👤 {userId?.slice(0, 20)}... | 📝 {sessionId.slice(0, 15)}... | 💬 {messages.filter(m => m.role !== 'system').length} messages
            </div>
          )}
        </div>

        {/* Messages */}
        <div className="flex-1 overflow-y-auto p-4 space-y-4">
          {messages.map((msg) => (
            <div
              key={msg.id}
              className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
            >
              <div
                className={`max-w-[85%] rounded-xl px-4 py-3 ${
                  msg.role === 'user'
                    ? 'bg-gradient-to-r from-violet-500 to-purple-600 text-white'
                    : msg.role === 'system'
                    ? 'bg-slate-700/50 text-slate-400 text-sm italic'
                    : 'bg-slate-700 text-slate-100'
                }`}
              >
                <p className="whitespace-pre-wrap">{msg.content}</p>
                
                {/* Source References */}
                {msg.metadata?.sources && msg.metadata.sources.length > 0 && (
                  <div className="mt-3 pt-3 border-t border-slate-600 space-y-1">
                    <p className="text-xs text-slate-400 font-medium">📎 参照元:</p>
                    {msg.metadata.sources.map((src, idx) => (
                      <div key={idx} className="flex items-center gap-2 text-xs">
                        <span className={`px-1.5 py-0.5 rounded ${
                          src.type === 'agentcore' ? 'bg-pink-500/30 text-pink-300' :
                          src.type === 'bedrock_kb' ? 'bg-blue-500/30 text-blue-300' :
                          'bg-green-500/30 text-green-300'
                        }`}>
                          {src.type === 'agentcore' ? '🧠' : src.type === 'bedrock_kb' ? '📚' : '🗄️'}
                          {src.type}
                        </span>
                        {src.score && <span className="text-slate-500">Score: {(src.score * 100).toFixed(0)}%</span>}
                      </div>
                    ))}
                  </div>
                )}
                
                {/* Processing Info */}
                {msg.metadata?.processingTime && (
                  <div className="mt-2 text-xs text-slate-400">
                    ⏱️ {msg.metadata.processingTime}ms | 
                    🤖 {msg.metadata.model} |
                    💾 {msg.metadata.memoryType || 'none'}
                  </div>
                )}
              </div>
            </div>
          ))}
          <div ref={messagesEndRef} />
        </div>

        {/* Input */}
        <form onSubmit={handleSubmit} className="p-4 border-t border-slate-700 bg-slate-800/30">
          <div className="flex gap-2">
            <input
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="メッセージを入力... (RAG + Memory で回答します)"
              disabled={isLoading || !sessionId}
              className="flex-1 px-4 py-3 bg-slate-700 border border-slate-600 rounded-xl text-white placeholder-slate-400 focus:outline-none focus:border-violet-500 disabled:opacity-50"
            />
            <button
              type="submit"
              disabled={isLoading || !input.trim() || !sessionId}
              className="px-6 py-3 bg-gradient-to-r from-violet-500 to-purple-600 text-white font-medium rounded-xl hover:opacity-90 disabled:opacity-50 disabled:cursor-not-allowed transition-opacity"
            >
              {isLoading ? '⏳' : '送信'}
            </button>
          </div>
        </form>
      </div>

      {/* Processing Logs Panel */}
      {showLogs && (
        <div className="w-1/3 flex flex-col bg-slate-900/50">
          <div className="p-3 border-b border-slate-700 bg-slate-800/50">
            <h3 className="text-sm font-semibold text-slate-300">📊 Processing Logs</h3>
            <p className="text-xs text-slate-500 mt-1">Real-time processing status</p>
          </div>
          
          <div className="flex-1 overflow-y-auto p-2 space-y-1 text-xs font-mono">
            {processingLogs.map((log) => (
              <div
                key={log.id}
                className={`p-2 rounded ${
                  log.status === 'pending' ? 'bg-yellow-500/10 border-l-2 border-yellow-500' :
                  log.status === 'success' ? 'bg-green-500/10 border-l-2 border-green-500' :
                  'bg-red-500/10 border-l-2 border-red-500'
                }`}
              >
                <div className="flex items-center gap-2">
                  <span className={`w-2 h-2 rounded-full ${
                    log.status === 'pending' ? 'bg-yellow-500 animate-pulse' :
                    log.status === 'success' ? 'bg-green-500' :
                    'bg-red-500'
                  }`} />
                  <span className={`px-1.5 py-0.5 rounded text-[10px] ${
                    log.source === 'agentcore' ? 'bg-pink-500/30 text-pink-300' :
                    log.source === 'bedrock_kb' ? 'bg-blue-500/30 text-blue-300' :
                    log.source === 's3_vectors' ? 'bg-green-500/30 text-green-300' :
                    'bg-violet-500/30 text-violet-300'
                  }`}>
                    {log.source}
                  </span>
                  <span className="text-slate-300 font-medium">{log.action}</span>
                </div>
                <p className="text-slate-400 mt-1 ml-4">{log.details}</p>
                {log.duration && (
                  <p className="text-slate-500 mt-0.5 ml-4">⏱️ {log.duration}ms</p>
                )}
              </div>
            ))}
            <div ref={logsEndRef} />
            
            {processingLogs.length === 0 && (
              <div className="text-center text-slate-500 py-8">
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
