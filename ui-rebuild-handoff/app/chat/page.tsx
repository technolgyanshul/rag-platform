'use client';

import React, { useState } from 'react';
import { DashboardLayout } from '@/components/dashboard-layout';
import { PageHeader } from '@/components/page-header';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { MessageSquare, Send } from 'lucide-react';

interface ChatMessage {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: Date;
  sources?: string[];
}

export default function ChatPage() {
  const [messages, setMessages] = useState<ChatMessage[]>([
    {
      id: '1',
      role: 'assistant',
      content: 'Hello! I\'m your RAG assistant. How can I help you today? I have access to your knowledge base and can answer questions based on your documents.',
      timestamp: new Date(Date.now() - 3600000),
    },
  ]);

  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);

  const handleSend = async () => {
    if (!input.trim()) return;

    const userMessage: ChatMessage = {
      id: Date.now().toString(),
      role: 'user',
      content: input,
      timestamp: new Date(),
    };

    setMessages([...messages, userMessage]);
    setInput('');
    setIsLoading(true);

    // Simulate API call
    setTimeout(() => {
      const assistantMessage: ChatMessage = {
        id: (Date.now() + 1).toString(),
        role: 'assistant',
        content: 'I\'ve reviewed your knowledge base and found relevant information. Based on the documents you\'ve uploaded, here\'s what I found...',
        timestamp: new Date(),
        sources: ['Product Documentation.pdf', 'API Reference.docx'],
      };
      setMessages((prev) => [...prev, assistantMessage]);
      setIsLoading(false);
    }, 1000);
  };

  return (
    <DashboardLayout user={{ email: 'user@example.com', name: 'John Doe' }}>
      <PageHeader
        title="RAG Chat"
        description="Query your knowledge base with AI assistance"
      />

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4 md:gap-6">
        {/* Main Chat */}
        <div className="lg:col-span-2 min-h-0">
          <Card className="flex flex-col h-[600px]">
            {/* Chat Messages */}
            <CardContent className="flex-1 overflow-y-auto p-6 space-y-4">
              {messages.map((message) => (
                <div
                  key={message.id}
                  className={`flex ${message.role === 'user' ? 'justify-end' : 'justify-start'}`}
                >
                  <div
                    className={`max-w-xs lg:max-w-md px-4 py-2 rounded-lg ${
                      message.role === 'user'
                        ? 'bg-accent text-accent-foreground'
                        : 'bg-muted text-muted-foreground'
                    }`}
                  >
                    <p className="text-sm">{message.content}</p>
                    {message.sources && message.sources.length > 0 && (
                      <div className="text-xs mt-2 space-y-1">
                        <p className="font-semibold">Sources:</p>
                        {message.sources.map((source) => (
                          <p key={source}>• {source}</p>
                        ))}
                      </div>
                    )}
                  </div>
                </div>
              ))}
              {isLoading && (
                <div className="flex justify-start">
                  <div className="bg-muted text-muted-foreground px-4 py-2 rounded-lg">
                    <p className="text-sm">Thinking...</p>
                  </div>
                </div>
              )}
            </CardContent>

            {/* Input Area */}
            <div className="border-t border-border p-4">
              <div className="flex gap-2">
                <Input
                  placeholder="Ask your question..."
                  value={input}
                  onChange={(e) => setInput(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter' && !e.shiftKey) {
                      e.preventDefault();
                      handleSend();
                    }
                  }}
                  disabled={isLoading}
                />
                <Button onClick={handleSend} disabled={isLoading}>
                  <Send size={18} />
                </Button>
              </div>
            </div>
          </Card>
        </div>

        {/* Sidebar */}
        <div className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle className="text-base">Query Settings</CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              <div>
                <label className="text-xs font-semibold text-foreground block mb-2">
                  Select Team
                </label>
                <select className="w-full px-3 py-2 border border-border rounded-lg text-sm bg-background text-foreground">
                  <option>Product Team</option>
                  <option>Engineering</option>
                </select>
              </div>
              <div>
                <label className="text-xs font-semibold text-foreground block mb-2">
                  Select Agent
                </label>
                <select className="w-full px-3 py-2 border border-border rounded-lg text-sm bg-background text-foreground">
                  <option>Support Agent</option>
                  <option>Documentation Agent</option>
                </select>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle className="text-base">Recent Queries</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-2 text-sm">
                <button className="w-full text-left px-3 py-2 rounded hover:bg-muted transition-colors text-foreground">
                  How do I integrate the API?
                </button>
                <button className="w-full text-left px-3 py-2 rounded hover:bg-muted transition-colors text-foreground">
                  What are the pricing tiers?
                </button>
                <button className="w-full text-left px-3 py-2 rounded hover:bg-muted transition-colors text-foreground">
                  How to deploy on production?
                </button>
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    </DashboardLayout>
  );
}
