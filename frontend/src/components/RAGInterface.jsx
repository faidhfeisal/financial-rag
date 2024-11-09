import React, { useState } from 'react';
import { Search, Book, ArrowRight, Loader2, BarChart, ThumbsUp, ThumbsDown } from 'lucide-react';
import { 
  Card, 
  CardContent, 
  CardDescription, 
  CardFooter, 
  CardHeader, 
  CardTitle,
  Alert,
  AlertDescription,
  Button,
  Tabs,
  TabsContent,
  TabsList,
  TabsTrigger,
  Badge,
  ScrollArea,
  Progress
} from './ui';

import DocumentManager from './DocumentManager';

const RAGInterface = () => {
  const [query, setQuery] = useState('');
  const [loading, setLoading] = useState(false);
  const [activeTab, setActiveTab] = useState('query');
  const [response, setResponse] = useState(null);
  const [error, setError] = useState(null);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!query.trim()) return;

    setLoading(true);
    setError(null);

    try {
      const res = await fetch('http://127.0.0.1:8000/api/v1/query', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query: query.trim() })
      });

      if (!res.ok) throw new Error('Query failed');
      
      const data = await res.json();
      setResponse(data);
    } catch (err) {
      setError('Failed to process query. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  const handleFeedback = async (isPositive) => {
    if (!response) return;
    
    try {
      await fetch('/api/v1/evaluation/feedback', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          query_id: response.query_id,
          rating: isPositive ? 5 : 1,
          helpful: isPositive
        })
      });
    } catch (err) {
      console.error('Failed to submit feedback:', err);
    }
  };

  return (
    <div className="max-w-6xl mx-auto p-6 space-y-8">
      <div className="space-y-2">
        <h1 className="text-3xl font-bold tracking-tight">
          Financial Regulations Assistant
        </h1>
        <p className="text-muted-foreground">
          Ask questions about financial regulations and compliance requirements
        </p>
      </div>

      <Tabs value={activeTab} onValueChange={setActiveTab} className="space-y-4">
        <TabsList>
          <TabsTrigger value="query">Query</TabsTrigger>
          <TabsTrigger value="documents">Documents</TabsTrigger>
          <TabsTrigger value="sources">Sources</TabsTrigger>
          <TabsTrigger value="metrics">Metrics</TabsTrigger>
        </TabsList>

        <TabsContent value="query" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Ask a Question</CardTitle>
              <CardDescription>
                Enter your question about financial regulations
              </CardDescription>
            </CardHeader>
            <CardContent>
              <form onSubmit={handleSubmit} className="space-y-4">
                <div className="relative">
                  <input
                    type="text"
                    value={query}
                    onChange={(e) => setQuery(e.target.value)}
                    placeholder="e.g., What are the key requirements of ISO 27001?"
                    className="w-full p-4 pr-12 rounded-lg border border-input bg-background"
                  />
                  <Button 
                    type="submit" 
                    size="icon"
                    disabled={loading}
                    className="absolute right-2 top-1/2 -translate-y-1/2"
                  >
                    {loading ? (
                      <Loader2 className="h-4 w-4 animate-spin" />
                    ) : (
                      <ArrowRight className="h-4 w-4" />
                    )}
                  </Button>
                </div>
              </form>
            </CardContent>
          </Card>

          {error && (
            <Alert variant="destructive">
              <AlertDescription>{error}</AlertDescription>
            </Alert>
          )}

          {response && (
            <Card>
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle>Response</CardTitle>
                <Badge variant="secondary">
                  Confidence: {(response.evaluation.confidence_score * 100).toFixed(1)}%
                </Badge>
              </CardHeader>
              <CardContent className="space-y-4">
                <ScrollArea className="h-[300px] rounded-md border p-4">
                  <div className="prose max-w-none">
                    {response.response}
                  </div>
                </ScrollArea>
              </CardContent>
              <CardFooter className="justify-between">
                <span className="text-sm text-muted-foreground">
                  Was this response helpful?
                </span>
                <div className="space-x-2">
                  <Button 
                    variant="outline" 
                    size="sm"
                    onClick={() => handleFeedback(true)}
                  >
                    <ThumbsUp className="h-4 w-4 mr-2" />
                    Yes
                  </Button>
                  <Button 
                    variant="outline" 
                    size="sm"
                    onClick={() => handleFeedback(false)}
                  >
                    <ThumbsDown className="h-4 w-4 mr-2" />
                    No
                  </Button>
                </div>
              </CardFooter>
            </Card>
          )}
        </TabsContent>

        <TabsContent value="documents">
          <DocumentManager />
        </TabsContent>

        <TabsContent value="sources">
          {response?.sources && (
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Book className="h-5 w-5" />
                  Source Documents
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-4">
                  {response.sources.map((source, idx) => (
                    <div key={idx} className="space-y-2">
                      <div className="flex items-center justify-between">
                        <h3 className="font-semibold">[{idx + 1}] {source.metadata.title}</h3>
                        <Badge variant="outline">
                          {(source.similarity * 100).toFixed(1)}% relevant
                        </Badge>
                      </div>
                      <p className="text-sm text-muted-foreground">
                        {source.content.substring(0, 200)}...
                      </p>
                      <Progress value={source.similarity * 100} className="h-2" />
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          )}
        </TabsContent>

        <TabsContent value="metrics">
          {response?.evaluation && (
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <BarChart className="h-5 w-5" />
                  Response Metrics
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="grid grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <p className="text-sm font-medium">Response Time</p>
                    <p className="text-2xl font-bold">
                      {response.evaluation.latency_ms.toFixed(0)}ms
                    </p>
                  </div>
                  <div className="space-y-2">
                    <p className="text-sm font-medium">Tokens Used</p>
                    <p className="text-2xl font-bold">
                      {response.evaluation.token_usage.total_tokens}
                    </p>
                  </div>
                  <div className="space-y-2">
                    <p className="text-sm font-medium">Source Documents</p>
                    <p className="text-2xl font-bold">
                      {response.sources.length}
                    </p>
                  </div>
                  <div className="space-y-2">
                    <p className="text-sm font-medium">Citations</p>
                    <p className="text-2xl font-bold">
                      {response.evaluation.citations.count}
                    </p>
                  </div>
                </div>
              </CardContent>
            </Card>
          )}
        </TabsContent>
      </Tabs>
    </div>
  );
};

export default RAGInterface;