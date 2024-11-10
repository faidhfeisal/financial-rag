import React, { useState, useRef, useCallback, useEffect } from 'react';
import { useAuth } from '../contexts/AuthContext';
import { api } from '../api';
import { 
  Send, 
  Upload, 
  Loader2, 
  FileText, 
  Trash2,
  MessageSquare, 
  BarChart2,
  Expand,
  Lightbulb,
  ThumbsUp,
  ThumbsDown,
  ChevronDown,
  ChevronUp
} from 'lucide-react';
import { cn } from '../lib/utils';

import { 
  Card,
  CardContent, 
  Badge, 
  Button,
  ScrollArea,
  Alert,
  AlertDescription,
  Progress,
  Collapsible,
  CollapsibleTrigger,
  CollapsibleContent
} from './ui';

// Streaming Message Component
const StreamingMessage = ({ message, isComplete }) => {
  console.log('StreamingMessage rendering:', { message, isComplete }); // Debug log
  return (
    <div className="flex items-start gap-4 rounded-lg p-4 bg-background">
      <div className="h-8 w-8 rounded-full bg-blue-500 flex items-center justify-center text-white">
        A
      </div>
      <div className="flex-1 space-y-2">
        <div className="prose max-w-none whitespace-pre-wrap">
          {message || ''}
          {!isComplete && (
            <span className="ml-1 inline-block w-2 h-4 bg-blue-500 animate-pulse" />
          )}
        </div>
      </div>
    </div>
  );
};

// Response Metrics Component
const ResponseMetrics = ({ metrics, sources, onFeedback }) => {
  console.log('Rendering metrics:', { metrics, sources });
  const [isExpanded, setIsExpanded] = useState(false);

  // Return null if metrics or sources aren't available yet
  if (!metrics || !sources) return null;

  // Ensure we have all required metrics properties
  const confidenceScore = metrics.confidence_score || 0;
  const latencyMs = metrics.latency_ms || 0;
  const tokenUsage = metrics.token_usage || {
    prompt_tokens: 0,
    completion_tokens: 0,
    total_tokens: 0
  };
  const citations = metrics.citations || {
    count: 0,
    present: false
  };

  return (
    <Collapsible 
      open={isExpanded} 
      onOpenChange={setIsExpanded}
      className="mt-4 space-y-2"
    >
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <Badge variant={confidenceScore > 0.8 ? "success" : "warning"}>
            {(confidenceScore * 100).toFixed(1)}% confidence
          </Badge>
          <span className="text-sm text-muted-foreground">
            {latencyMs.toFixed(0)}ms
          </span>
          <span className="text-sm text-muted-foreground">
            {tokenUsage.total_tokens} tokens
          </span>
        </div>
        <div className="flex items-center gap-2">
          <Button 
            variant="ghost" 
            size="sm"
            onClick={() => onFeedback(true)}
          >
            <ThumbsUp className="h-4 w-4 mr-1" />
            Helpful
          </Button>
          <Button 
            variant="ghost" 
            size="sm"
            onClick={() => onFeedback(false)}
          >
            <ThumbsDown className="h-4 w-4 mr-1" />
            Not Helpful
          </Button>
          <CollapsibleTrigger asChild>
            <Button variant="ghost" size="sm">
              {isExpanded ? (
                <ChevronUp className="h-4 w-4" />
              ) : (
                <ChevronDown className="h-4 w-4" />
              )}
            </Button>
          </CollapsibleTrigger>
        </div>
      </div>

      <CollapsibleContent className="space-y-4">
        <div className="grid grid-cols-2 gap-4 mt-4">
          <Card>
            <CardContent className="p-4">
              <h4 className="text-sm font-medium mb-2 flex items-center gap-2">
                <BarChart2 className="h-4 w-4" />
                Response Metrics
              </h4>
              <div className="space-y-2">
                <div>
                  <div className="flex justify-between text-sm">
                    <span>Response Time</span>
                    <span>{latencyMs.toFixed(0)}ms</span>
                  </div>
                  <Progress 
                    value={Math.min((latencyMs / 1000) * 100, 100)} 
                    className="h-2"
                  />
                </div>
                <div>
                  <div className="flex justify-between text-sm">
                    <span>Confidence Score</span>
                    <span>{(confidenceScore * 100).toFixed(1)}%</span>
                  </div>
                  <Progress 
                    value={confidenceScore * 100} 
                    className="h-2"
                  />
                </div>
                <div>
                  <div className="flex justify-between text-sm">
                    <span>Citations Used</span>
                    <span>{citations.count}</span>
                  </div>
                  <Progress 
                    value={(citations.count / (sources?.length || 1)) * 100} 
                    className="h-2"
                  />
                </div>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardContent className="p-4">
              <h4 className="text-sm font-medium mb-2 flex items-center gap-2">
                <Lightbulb className="h-4 w-4" />
                Token Usage
              </h4>
              <div className="space-y-2">
                <div className="flex justify-between text-sm">
                  <span>Prompt Tokens</span>
                  <span>{tokenUsage.prompt_tokens}</span>
                </div>
                <div className="flex justify-between text-sm">
                  <span>Completion Tokens</span>
                  <span>{tokenUsage.completion_tokens}</span>
                </div>
                <div className="flex justify-between text-sm font-medium">
                  <span>Total Tokens</span>
                  <span>{tokenUsage.total_tokens}</span>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>

        {sources && sources.length > 0 && (
          <Card>
            <CardContent className="p-4">
              <h4 className="text-sm font-medium mb-2 flex items-center gap-2">
                <FileText className="h-4 w-4" />
                Source Documents
              </h4>
              <div className="space-y-2">
                {sources.map((source, idx) => (
                  <div 
                    key={idx}
                    className="flex items-center justify-between p-2 rounded-lg border"
                  >
                    <div className="flex items-center gap-2 min-w-0">
                      <span className="text-sm font-medium text-muted-foreground">
                        [{idx + 1}]
                      </span>
                      <div className="truncate">
                        <p className="text-sm font-medium truncate">
                          {source.metadata?.title || 'Untitled Document'}
                        </p>
                        <p className="text-xs text-muted-foreground truncate">
                          {source.content?.substring(0, 100) || ''}...
                        </p>
                      </div>
                    </div>
                    <Badge className="ml-2" variant="secondary">
                      {(source.similarity * 100).toFixed(1)}%
                    </Badge>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        )}
      </CollapsibleContent>
    </Collapsible>
  );
};

const Message = ({ message, onFeedback }) => {
  console.log('Message render:', {
    content: message.content,
    type: message.type,
    isStreaming: message.isStreaming,
    contentLength: message.content?.length
  });

  return (
    <div className={cn(
      "flex items-start gap-4 rounded-lg p-4",
      message.type === 'user' ? 'bg-muted/50' : 'bg-background',
    )}>
      <div className={cn(
        "h-8 w-8 rounded-full flex items-center justify-center text-primary-foreground",
        message.type === 'user' ? 'bg-primary' : 'bg-blue-500'
      )}>
        {message.type === 'user' ? 'U' : 'A'}
      </div>

      <div className="flex-1 space-y-2">
        {/* Always show content div, even if empty */}
        <div className="prose max-w-none whitespace-pre-wrap min-h-[1.5em]">
          {message.content || ''}
          {message.isStreaming && (
            <span className="ml-1 inline-block w-2 h-4 bg-blue-500 animate-pulse" />
          )}
        </div>

        {message.type === 'assistant' && !message.isStreaming && message.metadata && (
          <ResponseMetrics 
            metrics={message.metadata.metrics}
            sources={message.sources}
            onFeedback={onFeedback}
          />
        )}
      </div>
    </div>
  );
};

// Main RAGInterface Component
const RAGInterface = () => {
  const [messages, setMessages] = useState([]);
  const [query, setQuery] = useState('');
  const [loading, setLoading] = useState(false);
  const [documents, setDocuments] = useState([]);
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const { user, logout } = useAuth(); 
  const [error, setError] = useState(null);
  const messagesEndRef = useRef(null);
  const fileInputRef = useRef(null);

  const scrollToBottom = useCallback(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, []);

  useEffect(() => {
    fetchDocuments();
  }, []);

  useEffect(() => {
    scrollToBottom();
  }, [messages, scrollToBottom]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!query.trim()) return;
  
    setLoading(true);
    setError(null);
  
    // Add user message immediately
    const newMessages = [
      ...messages,
      { type: 'user', content: query }
    ];
    setMessages(newMessages);
    setQuery('');
  
    try {
      // Create a new message for streaming response
      const streamingMessageId = Date.now();
      let currentContent = '';
      let sources = null;
      let metadata = null;
      
      setMessages(prev => [...prev, {
        id: streamingMessageId,
        type: 'assistant',
        content: '',
        isStreaming: true,
        sources: [],
        metadata: null
      }]);
  
      const response = await api.streamQuery(query.trim());
  
      if (!response.ok) throw new Error('Stream request failed');
      
      const reader = response.body.getReader();
      const decoder = new TextDecoder();
  
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
  
        const chunk = decoder.decode(value);
        const lines = chunk.split('\n');
  
        for (const line of lines) {
          if (!line.trim() || !line.startsWith('data: ')) continue;
          
          const data = line.slice(6); // Remove 'data: ' prefix
          if (data === '[DONE]') continue;
  
          try {
            const parsed = JSON.parse(data);
            console.log('Received stream data:', { type: parsed.type, data: parsed.data }); // Debug log
  
            switch (parsed.type) {
              case 'token':
                currentContent += parsed.data;
                console.log('Updated content:', currentContent); // Debug log
                setMessages(prev => prev.map(msg => 
                  msg.id === streamingMessageId
                    ? { ...msg, content: currentContent }
                    : msg
                ));
                break;
  
              case 'sources':
                sources = parsed.data;
                setMessages(prev => prev.map(msg => 
                  msg.id === streamingMessageId
                    ? { ...msg, sources }
                    : msg
                ));
                break;
  
              case 'metadata':
                metadata = {
                  metrics: {
                    confidence_score: parsed.data.confidence,
                    latency_ms: parsed.data.response_time,
                    token_usage: {
                      total_tokens: parsed.data.sources_count || 0,
                      prompt_tokens: 0,
                      completion_tokens: 0
                    },
                    citations: {
                      count: parsed.data.sources_count || 0,
                      present: true
                    }
                  }
                };
                setMessages(prev => prev.map(msg => 
                  msg.id === streamingMessageId
                    ? { ...msg, metadata }
                    : msg
                ));
                break;
  
              case 'error':
                setError(parsed.data);
                break;
            }
          } catch (e) {
            console.error('Error parsing stream data:', e, data);
          }
        }
      }
  
      // Mark streaming as complete
      setMessages(prev => prev.map(msg => 
        msg.id === streamingMessageId
          ? { 
              ...msg, 
              isStreaming: false,
              content: currentContent,
              sources: sources || msg.sources,
              metadata: metadata || msg.metadata
            }
          : msg
      ));
  
    } catch (err) {
      setError('Failed to process query. Please try again.');
      console.error('Query error:', err);
    } finally {
      setLoading(false);
      scrollToBottom();
    }
  };

  const handleFileUpload = async (event) => {
    const file = event.target.files?.[0];
    if (!file) return;
  
    setLoading(true);
    setError(null);
  
    try {
      const result = await api.uploadDocument(file, {
        title: file.name,
        document_type: "regulation",
        source: "upload",
        tags: ["regulation"],
        created_at: new Date().toISOString()
      });
      
      setMessages(prev => [...prev, {
        type: 'system',
        content: `Successfully uploaded: ${file.name}`,
        metadata: { document: result }
      }]);
  
      fetchDocuments();
    } catch (err) {
      setError(err.message || 'Failed to upload document');
      console.error('Upload error:', err);
    } finally {
      setLoading(false);
      event.target.value = '';
    }
  };

  const fetchDocuments = async () => {
    try {
      const data = await api.listDocuments();
      setDocuments(data.documents);
    } catch (err) {
      setError('Failed to load documents');
    }
  };

  const handleDelete = async (documentId) => {
    try {
      await api.deleteDocument(documentId);
      fetchDocuments();
    } catch (err) {
      setError('Failed to delete document');
    }
  };

  useEffect(() => {
    const loadInitialData = async () => {
      try {
        await fetchDocuments();
      } catch (error) {
        console.error('Failed to load initial data:', error);
      }
    };
  
    loadInitialData();
  }, []); // Only run on mount

  return (
    <div className="flex h-screen bg-background">
      {/* Main Chat Area */}
      <div className="flex-1 flex flex-col h-full">
        {/* Chat Messages */}
        <div className="border-b p-4">
          <div className="max-w-3xl mx-auto flex items-center justify-between">
            <h1 className="text-xl font-semibold">Financial Regulations Assistant</h1>
            <div className="flex items-center gap-4">
              <Badge>{user.role}</Badge>
              <Button variant="ghost" size="sm" onClick={logout}>
                Sign Out
              </Button>
            </div>
          </div>
        </div>
        <ScrollArea className="flex-1 p-4">
          <div className="max-w-3xl mx-auto space-y-4">
            {messages.length === 0 && (
              <div className="text-center text-muted-foreground py-8">
                <MessageSquare className="h-12 w-12 mx-auto mb-2 opacity-50" />
                <h3 className="text-lg font-semibold mb-2">
                  Welcome to Financial Regulations Assistant
                </h3>
                <p>
                  Ask questions about financial regulations or upload documents to get started
                </p>
              </div>
            )}

            {messages.map((message) => (
              <div key={message.id || message.content}>
                {message.type === 'assistant' && message.isStreaming ? (
                  <StreamingMessage
                    message={message.content}
                    isComplete={!message.isStreaming}
                  />
                ) : (
                  <Message
                    message={message}
                    onFeedback={async (isPositive) => {
                      try {
                        await fetch('/api/v1/evaluation/feedback', {
                          method: 'POST',
                          headers: { 'Content-Type': 'application/json' },
                          body: JSON.stringify({
                            query_id: message.metadata?.queryId,
                            rating: isPositive ? 5 : 1,
                            helpful: isPositive,
                            feedback_text: null
                          })
                        });
                      } catch (err) {
                        console.error('Failed to submit feedback:', err);
                      }
                    }}
                  />
                )}
              </div>
            ))}
            <div ref={messagesEndRef} />
          </div>
        </ScrollArea>

        {/* Input Area */}
        <div className="border-t p-4">
          <div className="max-w-3xl mx-auto">
            {error && (
              <Alert variant="destructive" className="mb-4">
                <AlertDescription>{error}</AlertDescription>
              </Alert>
            )}
            
            <form onSubmit={handleSubmit} className="flex gap-4">
            {(user.role === 'admin' || user.role === 'analyst') && (
              <Button
                type="button"
                variant="outline"
                size="icon"
                onClick={() => fileInputRef.current?.click()}
                disabled={loading}
              >
                <Upload className="h-4 w-4" />
              </Button>
            )}
              <input
                ref={fileInputRef}
                type="file"
                className="hidden"
                onChange={handleFileUpload}
                accept=".txt,.pdf,.doc,.docx"
              />
              
              <div className="flex-1 relative">
                <input
                  type="text"
                  value={query}
                  onChange={(e) => setQuery(e.target.value)}
                  placeholder="Ask about financial regulations..."
                  className="w-full rounded-md border border-input bg-background px-4 py-2 text-sm"
                  disabled={loading}
                />
              </div>

              <Button type="submit" disabled={loading || !query.trim()}>
                {loading ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
                ) : (
                  <Send className="h-4 w-4" />
                )}
              </Button>
            </form>
          </div>
        </div>
      </div>

      {/* Sidebar */}
      <div className={cn(
        "w-80 border-l bg-muted/10 transition-all duration-300",
        !sidebarOpen && "w-0 opacity-0"
      )}>
        <div className="p-4">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-lg font-semibold">Documents</h2>
            <Button
              variant="ghost"
              size="sm"
              onClick={() => setSidebarOpen(!sidebarOpen)}
            >
              {sidebarOpen ? "Hide" : "Show"}
            </Button>
          </div>

          <ScrollArea className="h-[calc(100vh-8rem)]">
            <div className="space-y-2">
              {documents.map((doc) => (
                <Card key={doc.document_id} className="p-2">
                  <CardContent className="p-0">
                    <div className="flex items-center gap-2">
                      <FileText className="h-4 w-4 text-blue-500" />
                      <div className="flex-1 min-w-0">
                        <p className="text-sm font-medium truncate">
                          {doc.metadata.title}
                        </p>
                        <p className="text-xs text-muted-foreground">
                          {new Date(doc.metadata.created_at).toLocaleDateString()}
                        </p>
                      </div>
                      {user.role === 'admin' && (
                        <Button
                          variant="ghost"
                          size="icon"
                          onClick={() => handleDelete(doc.document_id)}
                          className="h-6 w-6"
                        >
                          <Trash2 className="h-4 w-4 text-red-500" />
                        </Button>
                      )}
                    </div>
                  </CardContent>
                </Card>
              ))}

              {documents.length === 0 && (
                <div className="text-center text-muted-foreground py-8">
                  <FileText className="h-8 w-8 mx-auto mb-2 opacity-50" />
                  <p className="text-sm">No documents uploaded yet</p>
                </div>
              )}
            </div>
          </ScrollArea>
        </div>
      </div>
    </div>
  );
};

export default RAGInterface;