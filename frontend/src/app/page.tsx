// src/app/page.tsx
"use client";

import { ChatWindow, Message } from "@/components/ui/chat";
import { useRef, useState } from "react";

export default function Home() {
  const API_URL = "http://localhost:8000/query-with-rag";
  const [messages, setMessages] = useState<Message[]>([
    {
      id: "1",
      content:
        "Hello! I am SUSTEN AI assistant. How can I help you?",
      sender: {
        id: "susten-ai",
        name: "SUSTEN AI",
        avatar: "/icons/icon-72x72.png",
      },
      timestamp: new Date(),
    },
  ]);
  const [isLoading, setIsLoading] = useState(false);
  const [streamingMessageId, setStreamingMessageId] = useState<string | null>(
    null,
  );
  const abortControllerRef = useRef<AbortController | null>(null);

  const handleSendMessage = async (content: string) => {
    // Add user message immediately
    const userMessage: Message = {
      id: `user-${Date.now()}`,
      content,
      sender: {
        id: "user",
        name: "You",
      },
      timestamp: new Date(),
      isCurrentUser: true,
    };

    setMessages((prev) => [...prev, userMessage]);
    setIsLoading(true);

    // Create AI message placeholder for streaming
    const aiMessageId = `ai-${Date.now()}`;
    const aiMessage: Message = {
      id: aiMessageId,
      content: "",
      sender: {
        id: "susten-ai",
        name: "SUSTEN AI",
        avatar: "/icons/icon-72x72.png",
      },
      timestamp: new Date(),
    };

    setMessages((prev) => [...prev, aiMessage]);
    setStreamingMessageId(aiMessageId);

    // Create abort controller for this request
    abortControllerRef.current = new AbortController();

    const conversationContext = messages
      .filter((msg) => msg.sender.id !== "susten-ai") // Only include user messages for context
      .slice(0, -1) // Exclude the current message (last one) to avoid duplication
      .slice(-5) // Keep last 5 messages for context (after excluding current)
      .map((msg) => `User: ${msg.content}`)
      .join("\n");

    try {
      // Call streaming API
      const response = await fetch(API_URL, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          message: content,
          conversationHistory: conversationContext,
        }),
        signal: abortControllerRef.current.signal,
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      // Check if response is streaming
      const contentType = response.headers.get("content-type");
      console.log("📡 Response content-type:", contentType);

      if (contentType?.includes("text/event-stream")) {
        console.log("🔄 Handling streaming response");
        // Handle streaming response
        const reader = response.body?.getReader();
        const decoder = new TextDecoder();
        let accumulatedContent = "";

        if (reader) {
          while (true) {
            const { done, value } = await reader.read();
            if (done) break;

            const chunk = decoder.decode(value);
            const lines = chunk.split("\n");

            for (const line of lines) {
              if (line.startsWith("data: ")) {
                try {
                  const jsonString = line.slice(6).trim();
                  // Skip empty lines or incomplete data
                  if (!jsonString || jsonString === "") {
                    continue;
                  }

                  console.log("📥 Received streaming data:", jsonString.substring(0, 100) + "...");
                  const data = JSON.parse(jsonString);

                  if (data.type === "content") {
                    accumulatedContent += data.text;
                    console.log("📝 Accumulated content length:", accumulatedContent.length);
                    // Update the streaming message in real-time
                    setMessages((prev) =>
                      prev.map((msg) =>
                        msg.id === aiMessageId
                          ? { ...msg, content: accumulatedContent }
                          : msg,
                      ),
                    );
                  } else if (data.type === "done") {
                    console.log("✅ Streaming completed");
                    // Streaming completed
                    break;
                  } else if (data.type === "error") {
                    throw new Error(data.error || "Streaming error occurred");
                  }
                } catch (parseError) {
                  // Log the problematic line for debugging
                  console.warn("Failed to parse streaming data:", {
                    line: line,
                    error: parseError,
                    lineLength: line.length,
                  });
                  // Continue processing other lines instead of failing
                  continue;
                }
              } else if (line.trim() && !line.startsWith("data:")) {
                // Handle plain JSON streaming (non-SSE format)
                try {
                  const data = JSON.parse(line.trim());

                  if (data.type === "content") {
                    accumulatedContent += data.text;
                    setMessages((prev) =>
                      prev.map((msg) =>
                        msg.id === aiMessageId
                          ? { ...msg, content: accumulatedContent }
                          : msg,
                      ),
                    );
                  } else if (data.type === "done") {
                    break;
                  } else if (data.type === "error") {
                    throw new Error(data.error || "Streaming error occurred");
                  }
                } catch (parseError) {
                  console.warn("Failed to parse plain JSON streaming data:", {
                    line: line,
                    error: parseError,
                  });
                  continue;
                }
              }
            }
          }
        }
      } else {
        // Handle non-streaming response (fallback)
        const data = await response.json();
        if (data.error) {
          throw new Error(data.error);
        }

        setMessages((prev) =>
          prev.map((msg) =>
            msg.id === aiMessageId ? { ...msg, content: data.response } : msg,
          ),
        );
      }
    } catch (error) {
      console.error("Error calling chat API:", error);

      // Handle aborted requests
      if (error instanceof Error && error.name === "AbortError") {
        // Remove the placeholder message if request was aborted
        setMessages((prev) => prev.filter((msg) => msg.id !== aiMessageId));
        return;
      }

      // Add error message
      const errorMessage =
        error instanceof Error ? error.message : "Unknown error occurred";
      setMessages((prev) =>
        prev.map((msg) =>
          msg.id === aiMessageId
            ? {
              ...msg,
              content: `I apologize, but I'm experiencing technical difficulties: ${errorMessage}. Please try again in a moment.`,
            }
            : msg,
        ),
      );
    } finally {
      setIsLoading(false);
      setStreamingMessageId(null);
      abortControllerRef.current = null;
    }
  };

  return (
    <div className="mx-auto flex h-[calc(100vh-3.5rem)] max-w-6xl flex-col p-4 sm:p-6">
      {/* Main Chat Interface */}
      <div className="flex min-h-0 flex-1 justify-center">
        {/* Chat Window */}
        <div className="flex min-h-0 w-full max-w-4xl flex-col">
          <ChatWindow
            messages={messages}
            currentUserId="user"
            onSendMessage={handleSendMessage}
            title="SUSTEN FAQ Bot"
            subtitle={
              isLoading
                ? streamingMessageId
                  ? "Answering..."
                  : "Thinking..."
                : "On standby..."
            }
            status={isLoading ? "typing" : "online"}
            className="min-h-0 flex-1"
            isStreaming={!!streamingMessageId}
            streamingMessageId={streamingMessageId}
          />
        </div>
      </div>
    </div>
  );
}
