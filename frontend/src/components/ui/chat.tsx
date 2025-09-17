"use client";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardFooter,
  CardHeader,
} from "@/components/ui/card";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Input } from "@/components/ui/input";
import { useTypewriter } from "@/hooks/useTypewriter";
import { cn } from "@/lib/utils";
import "highlight.js/styles/github.css";
import { Loader2, MoreVertical, Send } from "lucide-react";
import * as React from "react";
import ReactMarkdown from "react-markdown";
import rehypeHighlight from "rehype-highlight";
import remarkGfm from "remark-gfm";

export interface Message {
  id: string;
  content: string;
  sender: {
    id: string;
    name: string;
    avatar?: string;
  };
  timestamp: Date;
  isCurrentUser?: boolean;
}

export interface ChatWindowProps extends React.HTMLAttributes<HTMLDivElement> {
  messages: Message[];
  currentUserId?: string;
  onSendMessage?: (content: string) => void;
  title?: string;
  subtitle?: string;
  status?: "online" | "offline" | "typing";
  isStreaming?: boolean;
  streamingMessageId?: string | null;
}

const ChatWindow = React.forwardRef<HTMLDivElement, ChatWindowProps>(
  (
    {
      className,
      messages,
      currentUserId,
      onSendMessage,
      title,
      subtitle,
      status,
      isStreaming = false,
      streamingMessageId = null,
      ...props
    },
    ref,
  ) => {
    const [inputValue, setInputValue] = React.useState("");
    const messagesEndRef = React.useRef<HTMLDivElement>(null);
    const scrollContainerRef = React.useRef<HTMLDivElement>(null);

    const scrollToBottom = () => {
      if (scrollContainerRef.current) {
        scrollContainerRef.current.scrollTop =
          scrollContainerRef.current.scrollHeight;
      }
    };

    React.useEffect(() => {
      scrollToBottom();
    }, [messages]);

    const handleSend = () => {
      if (inputValue.trim() && onSendMessage) {
        onSendMessage(inputValue.trim());
        setInputValue("");
      }
    };

    const handleKeyPress = (e: React.KeyboardEvent<HTMLInputElement>) => {
      if (e.key === "Enter" && !e.shiftKey) {
        e.preventDefault();
        handleSend();
      }
    };

    return (
      <Card ref={ref} className={cn("flex flex-col", className)} {...props}>
        <ChatHeader title={title} subtitle={subtitle} status={status} />
        <CardContent
          ref={scrollContainerRef}
          className="min-h-0 flex-1 overflow-y-auto p-4"
        >
          <MessageList
            messages={messages}
            currentUserId={currentUserId}
            isStreaming={isStreaming}
            streamingMessageId={streamingMessageId}
          />
          <div ref={messagesEndRef} />
        </CardContent>
        <CardFooter className="flex-shrink-0 p-4">
          <ChatInput
            value={inputValue}
            onChange={setInputValue}
            onSend={handleSend}
            onKeyPress={handleKeyPress}
            disabled={isStreaming}
          />
        </CardFooter>
      </Card>
    );
  },
);
ChatWindow.displayName = "ChatWindow";

interface ChatHeaderProps {
  title?: string;
  subtitle?: string;
  status?: "online" | "offline" | "typing";
}

const ChatHeader = React.forwardRef<HTMLDivElement, ChatHeaderProps>(
  ({ title = "Chat", subtitle, status }, ref) => {
    return (
      <CardHeader
        ref={ref}
        className="flex flex-row items-center justify-between space-y-0 pb-3"
      >
        <div className="flex items-center space-x-4">
          <div>
            <h3 className="text-lg font-semibold">{title}</h3>
            {subtitle && (
              <p className="text-sm text-muted-foreground">{subtitle}</p>
            )}
          </div>
          {status && (
            <Badge
              variant={status === "online" ? "default" : "secondary"}
              className="ml-2"
            >
              {status === "typing" && (
                <Loader2 className="mr-1 h-3 w-3 animate-spin" />
              )}
              {status}
            </Badge>
          )}
        </div>
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button variant="ghost" size="icon">
              <MoreVertical className="h-4 w-4" />
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end">
            <DropdownMenuItem>Clear chat</DropdownMenuItem>
            <DropdownMenuItem>Export chat</DropdownMenuItem>
            <DropdownMenuItem>Settings</DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      </CardHeader>
    );
  },
);
ChatHeader.displayName = "ChatHeader";

interface MessageListProps {
  messages: Message[];
  currentUserId?: string;
  isStreaming?: boolean;
  streamingMessageId?: string | null;
}

const MessageList = React.forwardRef<HTMLDivElement, MessageListProps>(
  (
    { messages, currentUserId, isStreaming = false, streamingMessageId = null },
    ref,
  ) => {
    return (
      <div ref={ref} className="space-y-4">
        {messages.map((message) => (
          <MessageItem
            key={message.id}
            message={message}
            isCurrentUser={
              message.isCurrentUser ?? message.sender.id === currentUserId
            }
            isStreaming={isStreaming && message.id === streamingMessageId}
          />
        ))}
      </div>
    );
  },
);
MessageList.displayName = "MessageList";

interface MessageItemProps {
  message: Message;
  isCurrentUser: boolean;
  isStreaming?: boolean;
}

const MessageItem = React.forwardRef<HTMLDivElement, MessageItemProps>(
  ({ message, isCurrentUser, isStreaming = false }, ref) => {
    const { displayedText, isTyping } = useTypewriter({
      text: message.content,
      speed: 20,
      enabled: isStreaming && !isCurrentUser,
    });

    const contentToShow =
      isStreaming && !isCurrentUser ? displayedText : message.content;

    return (
      <div
        ref={ref}
        className={cn(
          "flex items-start space-x-2",
          isCurrentUser && "flex-row-reverse space-x-reverse",
        )}
      >
        <div
          className={cn(
            "flex max-w-[70%] flex-col",
            isCurrentUser && "items-end",
          )}
        >
          <div
            className={cn(
              "relative rounded-lg px-3 py-2",
              isCurrentUser ? "bg-secondary text-secondary-foreground" : "bg-muted",
            )}
          >
            <div className="markdown-content text-sm">
              <ReactMarkdown
                remarkPlugins={[remarkGfm]}
                rehypePlugins={[rehypeHighlight]}
                components={{
                  code: ({ children, ...props }) => (
                    <code {...props}>{children}</code>
                  ),
                  a: ({ children, href }) => (
                    <a href={href} target="_blank" rel="noopener noreferrer">
                      {children}
                    </a>
                  ),
                }}
              >
                {contentToShow}
              </ReactMarkdown>
            </div>
            {(isStreaming || isTyping) && !isCurrentUser && (
              <div className="ml-1 inline-flex items-center">
                <div className="flex space-x-1">
                  <div className="h-1 w-1 animate-pulse rounded-full bg-current"></div>
                  <div
                    className="h-1 w-1 animate-pulse rounded-full bg-current"
                    style={{ animationDelay: "0.2s" }}
                  ></div>
                  <div
                    className="h-1 w-1 animate-pulse rounded-full bg-current"
                    style={{ animationDelay: "0.4s" }}
                  ></div>
                </div>
              </div>
            )}
          </div>
          <span className="mt-1 text-xs text-muted-foreground">
            {message.timestamp.toLocaleTimeString([], {
              hour: "2-digit",
              minute: "2-digit",
            })}
          </span>
        </div>
      </div>
    );
  },
);
MessageItem.displayName = "MessageItem";

interface ChatInputProps {
  value: string;
  onChange: (value: string) => void;
  onSend: () => void;
  onKeyPress: (e: React.KeyboardEvent<HTMLInputElement>) => void;
  disabled?: boolean;
}

const ChatInput = React.forwardRef<HTMLDivElement, ChatInputProps>(
  ({ value, onChange, onSend, onKeyPress, disabled = false }, ref) => {
    return (
      <div ref={ref} className="flex w-full items-center space-x-2">
        <Input
          placeholder={disabled ? "回答しています・・・" : "質問を入力して下さい。"}
          value={value}
          onChange={(e) => onChange(e.target.value)}
          onKeyPress={onKeyPress}
          className="flex-1"
          disabled={disabled}
        />
        <Button
          onClick={onSend}
          size="icon"
          variant="secondary"
          disabled={!value.trim() || disabled}
        >
          {disabled ? (
            <Loader2 className="h-4 w-4 animate-spin" />
          ) : (
            <Send className="h-4 w-4" />
          )}
        </Button>
      </div>
    );
  },
);
ChatInput.displayName = "ChatInput";

export { ChatHeader, ChatInput, ChatWindow, MessageItem, MessageList };
