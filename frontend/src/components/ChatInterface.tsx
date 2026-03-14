import React, { useState, useEffect, useRef } from 'react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Card } from '@/components/ui/card';
import { Collapsible } from '@/components/ui/collapsible';
import { Send, Bot, User, Loader2, Sparkles, FileText, Paperclip, Moon, Sun, Wifi, WifiOff, Square } from 'lucide-react';
import { cn } from '@/lib/utils';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import rehypeHighlight from 'rehype-highlight';
import 'highlight.js/styles/github-dark.css';

interface ThinkingStep {
  step: string;
  content: string;
  timestamp?: Date;
  id?: string; // 添加唯一 ID
}

interface Message {
  id: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  thinkingSteps?: ThinkingStep[];
  data?: any;
  timestamp?: Date;
}

const ChatInterface: React.FC = () => {
  const [messages, setMessages] = useState<Message[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [clientId, setClientId] = useState('');
  const [input, setInput] = useState('');
  const [isConnected, setIsConnected] = useState(false);
  const [theme, setTheme] = useState<'light' | 'dark'>('light');
  const [isStopping, setIsStopping] = useState(false); // 用于跟踪是否正在停止
  const socketRef = useRef<WebSocket | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    const id = `client_${Math.random().toString(36).substr(2, 9)}`;
    setClientId(id);
  }, []);

  useEffect(() => {
    if (clientId) {
      const socket = new WebSocket(`ws://localhost:8000/ws/${clientId}`);

      socket.onopen = () => {
        console.log('WebSocket connected');
        setIsConnected(true);
      };

      socket.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          
          // 忽略连接成功的消息，只显示实际的回答内容
          if (data.type === 'connected' || (data.content && data.content.includes('连接成功'))) {
            return;
          }
          
          if (data.type === 'thinking') {
            // 将思考过程累积到最后一条助手消息中
            setMessages(prev => {
              if (prev.length === 0) return prev;
              
              // 找到最后一条助手消息
              const lastAssistantMsgIndex = prev.length - 1;
              const lastMsg = prev[lastAssistantMsgIndex];
              
              if (lastMsg && lastMsg.role === 'assistant') {
                // 追加思考步骤
                if (!lastMsg.thinkingSteps) {
                  lastMsg.thinkingSteps = [];
                }
                
                // 检查是否已存在相同的思考步骤（避免重复）
                const exists = lastMsg.thinkingSteps.some(
                  s => s.step === data.step && s.content === data.content
                );
                
                if (!exists) {
                  lastMsg.thinkingSteps.push({
                    step: data.step,
                    content: data.content,
                    timestamp: new Date(),
                    id: `${data.step}-${Date.now()}`
                  });
                }
                return [...prev];
              }
              return prev;
            });
          } else if (data.type === 'tool_call') {
            // 工具调用 - 也显示在思考过程中
            setMessages(prev => {
              if (prev.length === 0) return prev;
              
              // 找到最后一条助手消息
              const lastAssistantMsgIndex = prev.length - 1;
              const lastMsg = prev[lastAssistantMsgIndex];
              
              if (lastMsg && lastMsg.role === 'assistant') {
                if (!lastMsg.thinkingSteps) {
                  lastMsg.thinkingSteps = [];
                }
                
                // 检查是否已存在相同的工具调用（避免重复）
                const exists = lastMsg.thinkingSteps.some(
                  s => s.step === `调用工具：${data.tool}` && s.content === data.status
                );
                
                if (!exists) {
                  lastMsg.thinkingSteps.push({
                    step: `调用工具：${data.tool}`,
                    content: data.status,
                    timestamp: new Date(),
                    id: `tool-${data.tool}-${Date.now()}`
                  });
                }
                return [...prev];
              }
              return prev;
            });
          } else if (data.type === 'answer_stream') {
            // 流式回答 - 逐步更新最后一条助手消息
            setMessages(prev => {
              if (prev.length === 0) return prev;
              
              const lastAssistantMsgIndex = prev.length - 1;
              const lastMsg = prev[lastAssistantMsgIndex];
              
              if (lastMsg && lastMsg.role === 'assistant') {
                // 累积内容（包括 is_done 时也要累积）
                if (data.content) {
                  lastMsg.content = (lastMsg.content || '') + data.content;
                }
                // 如果是完成消息，添加来源信息
                if (data.is_done) {
                  lastMsg.data = data.data;
                  setIsLoading(false);
                }
                return [...prev];
              }
              return prev;
            });
          } else if (data.type === 'answer' || data.type === 'result') {
            // 最终回答 - 更新最后一条助手消息
            setMessages(prev => {
              if (prev.length === 0) return prev;
              
              const lastAssistantMsgIndex = prev.length - 1;
              const lastMsg = prev[lastAssistantMsgIndex];
              
              if (lastMsg && lastMsg.role === 'assistant') {
                lastMsg.content = data.content;
                lastMsg.data = data.data;
                setIsLoading(false);
                return [...prev];
              }
              return prev;
            });
          }
        } catch (error) {
          console.error('WebSocket message parsing error:', error);
        }
      };

      socket.onclose = () => {
        console.log('WebSocket disconnected');
        setIsConnected(false);
      };

      socketRef.current = socket;

      return () => {
        socket.close();
      };
    }
  }, [clientId]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  useEffect(() => {
    if (theme === 'dark') {
      document.documentElement.classList.add('dark');
    } else {
      document.documentElement.classList.remove('dark');
    }
  }, [theme]);

  useEffect(() => {
    // 初始化时设置主题为浅色
    setTheme('light');
  }, []);

  const toggleTheme = () => {
    setTheme(theme === 'dark' ? 'light' : 'dark');
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim()) return;

    const question = input;

    const userMessage: Message = {
      id: Date.now().toString(),
      role: 'user',
      content: question,
      timestamp: new Date()
    };
    setMessages(prev => [...prev, userMessage]);
    setInput('');
    setIsLoading(true);
    setIsStopping(false); // 重置停止状态

    // 创建一个空的助手消息用于接收思考过程和最终回答
    const assistantMessageId = `assistant-${Date.now()}`;
    setMessages(prev => [...prev, {
      id: assistantMessageId,
      role: 'assistant',
      content: '',
      thinkingSteps: [],
      timestamp: new Date()
    }]);

    try {
      if (socketRef.current && socketRef.current.readyState === WebSocket.OPEN) {
        socketRef.current.send(JSON.stringify({
          type: 'query',
          content: question,
          clientId
        }));
      }
    } catch (error) {
      console.error('Failed to send message:', error);
      setIsLoading(false);
    }
    inputRef.current?.focus();
  };

  const handleStop = () => {
    // 发送停止信号
    setIsStopping(true);
    setIsLoading(false);
    
    // 可以选择关闭 WebSocket 连接或者发送停止消息
    if (socketRef.current && socketRef.current.readyState === WebSocket.OPEN) {
      socketRef.current.send(JSON.stringify({
        type: 'stop',
        clientId
      }));
    }
    
    // 重置状态
    setTimeout(() => setIsStopping(false), 1000);
  };

  const formatTime = (date: Date) => {
    return date.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' });
  };

  const fetchFileContent = async (filePath: string) => {
    try {
      // 调用后端 API 获取文件内容
      const url = `http://localhost:8000/api/file?path=${encodeURIComponent(filePath)}`;
      // 在新窗口打开文件预览
      window.open(url, '_blank');
    } catch (error) {
      console.error('Failed to fetch file content:', error);
      alert('无法打开文件预览');
    }
  };

  return (
    <div className={cn(
      "h-screen overflow-y-auto transition-colors duration-300",
      theme === 'dark' ? "bg-[var(--color-background)] dark" : "bg-[var(--color-background)]"
    )}>
      <div className="max-w-4xl mx-auto w-full min-h-screen flex flex-col">
        <header className="sticky top-0 z-10 border-b border-[var(--color-border)] px-6 py-4 bg-[var(--color-background)]">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-full bg-[var(--color-primary)]/10 flex items-center justify-center">
                <Sparkles className="w-5 h-5 text-[var(--color-primary)]" />
              </div>
              <div>
                <h1 className="text-xl font-semibold text-[var(--color-foreground)]">企业知识库检索工具</h1>
                <p className="text-sm text-[var(--color-muted-foreground)]">基于Agent Skills的无向量渐进式检索引擎</p>
              </div>
            </div>
            
            <div className="flex items-center gap-4">
              <div className="flex items-center gap-2 px-3 py-1.5 rounded-full bg-[var(--color-muted)]">
                {isConnected ? (
                  <>
                    <Wifi className="w-4 h-4 text-green-500" />
                    <span className="text-xs text-[var(--color-muted-foreground)]">{clientId}</span>
                  </>
                ) : (
                  <>
                    <WifiOff className="w-4 h-4 text-red-500" />
                    <span className="text-xs text-[var(--color-muted-foreground)]">未连接</span>
                  </>
                )}
              </div>
              
              <Button
                variant="ghost"
                size="icon"
                onClick={toggleTheme}
                className="w-10 h-10"
              >
                {theme === 'dark' ? (
                  <Sun className="w-5 h-5" />
                ) : (
                  <Moon className="w-5 h-5" />
                )}
              </Button>
            </div>
          </div>
        </header>

        <div className="flex-1 px-6 py-4">
          {messages.length === 0 && (
            <div className="h-full flex items-center justify-center">
              <div className="text-center max-w-md">
                <div className="w-16 h-16 rounded-full bg-[var(--color-primary)]/10 flex items-center justify-center mx-auto mb-4">
                  <Bot className="w-8 h-8 text-[var(--color-primary)]" />
                </div>
                <h2 className="text-2xl font-semibold mb-2 text-[var(--color-foreground)]">欢迎使用知识库检索工具</h2>
                <p className="text-[var(--color-muted-foreground)] mb-6">
                  我可以帮助您检索知识库中的信息，支持Markdown、PDF、Excel等多种文件格式。
                </p>
                <div className="grid gap-3">
                  <Card 
                    className="p-4 cursor-pointer hover:bg-[var(--color-accent)] transition-colors text-left border border-[var(--color-border)] bg-[var(--color-card)]"
                    onClick={() => setInput("2026年AI Agent技术有哪些关键发展趋势？")}
                  >
                    <div className="flex items-start gap-3">
                      <FileText className="w-5 h-5 text-[var(--color-primary)] mt-0.5" />
                      <div>
                        <p className="font-medium text-[var(--color-foreground)]">查询业务需求</p>
                        <p className="text-sm text-[var(--color-muted-foreground)]">
                          "2026年AI Agent技术有哪些关键发展趋势？"
                        </p>
                      </div>
                    </div>
                  </Card>
                  <Card 
                    className="p-4 cursor-pointer hover:bg-[var(--color-accent)] transition-colors text-left border border-[var(--color-border)] bg-[var(--color-card)]"
                    onClick={() => setInput("XSS是什么？")}
                  >
                    <div className="flex items-start gap-3">
                      <FileText className="w-5 h-5 text-[var(--color-primary)] mt-0.5" />
                      <div>
                        <p className="font-medium text-[var(--color-foreground)]">查询技术文档</p>
                        <p className="text-sm text-[var(--color-muted-foreground)]">
                          "XSS是什么？"
                        </p>
                      </div>
                    </div>
                  </Card>
                </div>
              </div>
            </div>
          )}

          <div className="space-y-6">
            {messages.map((message) => (
              <div
                key={message.id}
                className={cn(
                  "flex gap-4",
                  message.role === 'user' && "flex-row-reverse"
                )}
              >
                <div className={cn(
                  "w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0",
                  message.role === 'user' 
                    ? "bg-[var(--color-primary)] text-[var(--color-primary-foreground)]" 
                    : "bg-[var(--color-muted)]"
                )}>
                  {message.role === 'user' ? (
                    <User className="w-4 h-4" />
                  ) : (
                    <Bot className="w-4 h-4" />
                  )}
                </div>
                <div className={cn(
                  "flex-1 max-w-[80%]",
                  message.role === 'user' && "flex flex-col items-end"
                )}>
                  <Card className={cn(
                    "p-4 border user-bubble",
                    message.role === 'user' 
                      ? "bg-[var(--color-primary)] text-[var(--color-primary-foreground)] border-[var(--color-primary)]" 
                      : "bg-[var(--color-muted)] border-[var(--color-border)]"
                  )}>
                    {message.thinkingSteps && message.thinkingSteps.length > 0 && (
                      <div className="mb-3">
                        <Collapsible 
                          title={`思考过程 (${message.thinkingSteps.length} 步)`}
                          defaultOpen={true}
                        >
                          <div className="space-y-2 max-h-[16rem] overflow-y-auto pr-2">
                            {message.thinkingSteps.map((step, index) => (
                              <div key={step.id || index} className="text-xs">
                                <div className="font-semibold text-[var(--color-foreground)] mb-1">
                                  {step.step}
                                </div>
                                <div className="text-[var(--color-muted-foreground)] pl-2 border-l-2 border-[var(--color-border)]">
                                  {step.content}
                                </div>
                              </div>
                            ))}
                          </div>
                        </Collapsible>
                      </div>
                    )}
                    
                    {message.content && (
                      <div className="border-t border-[var(--color-border)]/50">
                        <div className={cn(
                          "prose prose-sm max-w-none",
                          message.role === 'user' 
                            ? "prose-invert" 
                            : "prose-invert dark:prose-invert"
                        )}>
                          <ReactMarkdown
                            remarkPlugins={[remarkGfm]}
                            rehypePlugins={[rehypeHighlight]}
                            components={{
                              code({ node, inline, className, children, ...props }: any) {
                                if (inline) {
                                  return (
                                    <code className="bg-[var(--color-muted)] px-1.5 py-0.5 rounded text-sm" {...props}>
                                      {children}
                                    </code>
                                  );
                                }
                                return (
                                  <code className={className} {...props}>
                                    {children}
                                  </code>
                                );
                              },
                              pre({ children }: any) {
                                return (
                                  <pre className="bg-[var(--color-muted)] rounded-lg p-4 overflow-x-auto">
                                    {children}
                                  </pre>
                                );
                              },
                              table({ children }: any) {
                                return (
                                  <div className="overflow-x-auto my-4">
                                    <table className="min-w-full border border-[var(--color-border)]">
                                      {children}
                                    </table>
                                  </div>
                                );
                              },
                              th({ children }: any) {
                                return (
                                  <th className="border border-[var(--color-border)] px-4 py-2 bg-[var(--color-muted)] font-semibold">
                                    {children}
                                  </th>
                                );
                              },
                              td({ children }: any) {
                                return (
                                  <td className="border border-[var(--color-border)] px-4 py-2">
                                    {children}
                                  </td>
                                );
                              },
                              p({ children }: any) {
                                return <p className="text-inherit">{children}</p>;
                              },
                              strong({ children }: any) {
                                return <strong className="text-inherit font-semibold">{children}</strong>;
                              },
                            }}
                          >
                            {message.content}
                          </ReactMarkdown>
                        </div>
                      </div>
                    )}
                    
                    {message.data?.sources && message.data.sources.length > 0 && (
                      <div className="mt-3 pt-3 border-t border-[var(--color-border)]/50">
                        <p className="text-xs font-semibold mb-2 opacity-70">文件来源:</p>
                        <ul className="text-xs space-y-1 opacity-90">
                          {message.data.sources.map((source: string, i: number) => {
                            // 提取文件名（去掉路径）
                            const fileName = source.split(/[\\/]/).pop() || source;
                            return (
                              <li key={i} className="flex items-center gap-1">
                                <FileText className="w-3 h-3" />
                                <a 
                                  href="#"
                                  onClick={(e) => {
                                    e.preventDefault();
                                    // 调用后端 API 获取文件内容
                                    fetchFileContent(source);
                                  }}
                                  className="hover:underline hover:text-[var(--color-primary)] transition-colors cursor-pointer"
                                >
                                  {fileName}
                                </a>
                              </li>
                            );
                          })}
                        </ul>
                      </div>
                    )}
                  </Card>
                  <p className="text-xs text-[var(--color-muted-foreground)] mt-1 px-1">
                    {message.timestamp ? formatTime(message.timestamp) : ''}
                  </p>
                </div>
              </div>
            ))}

            <div ref={messagesEndRef} />
          </div>
        </div>

        <div className="sticky bottom-0 border-t border-[var(--color-border)] px-6 py-4 bg-[var(--color-background)]">
          <form onSubmit={handleSubmit} className="flex gap-3">
            <div className="flex-1 relative">
              <Input
                ref={inputRef}
                value={input}
                onChange={(e) => setInput(e.target.value)}
                placeholder="请输入您的问题..."
                disabled={isLoading}
                className="pr-4 bg-[var(--color-background)] border-[var(--color-input)] text-[var(--color-foreground)]"
              />
              {/* 文件附件按钮暂时隐藏 */}
              {/* <Button
                type="button"
                variant="ghost"
                size="icon"
                className="absolute right-1 top-1/2 -translate-y-1/2 h-8 w-8"
                disabled={isLoading}
              >
                <Paperclip className="w-4 h-4" />
              </Button> */}
            </div>
            <Button 
              type={isLoading ? "button" : "submit"} 
              disabled={(!isLoading && !input.trim())}
              onClick={isLoading ? handleStop : undefined}
              variant={isLoading ? "destructive" : "default"}
              size="icon"
              className="h-10 w-10"
            >
              {isStopping ? (
                <Loader2 className="w-4 h-4 animate-spin" />
              ) : isLoading ? (
                <Square className="w-4 h-4" />
              ) : (
                <Send className="w-4 h-4" />
              )}
            </Button>
          </form>
          <p className="text-xs text-[var(--color-muted-foreground)] mt-2 text-center">
            {/* 支持 Markdown、PDF、Excel 等文件格式 */}
          </p>
        </div>
      </div>
    </div>
  );
};

export default ChatInterface;
