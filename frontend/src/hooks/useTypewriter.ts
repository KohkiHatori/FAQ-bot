import { useEffect, useState } from "react";

interface UseTypewriterOptions {
  text: string;
  speed?: number;
  enabled?: boolean;
}

export function useTypewriter({
  text,
  speed = 30,
  enabled = true,
}: UseTypewriterOptions) {
  const [displayedText, setDisplayedText] = useState("");
  const [isTyping, setIsTyping] = useState(false);

  useEffect(() => {
    if (!enabled) {
      setDisplayedText(text);
      setIsTyping(false);
      return;
    }

    if (text.length === 0) {
      setDisplayedText("");
      setIsTyping(false);
      return;
    }

    // If text is shorter than displayed text, reset immediately
    if (text.length < displayedText.length) {
      setDisplayedText(text);
      setIsTyping(text.length > 0);
      return;
    }

    // If text hasn't changed, don't restart typing
    if (text === displayedText) {
      setIsTyping(false);
      return;
    }

    setIsTyping(true);

    const timer = setTimeout(() => {
      if (displayedText.length < text.length) {
        setDisplayedText(text.slice(0, displayedText.length + 1));
      } else {
        setIsTyping(false);
      }
    }, speed);

    return () => clearTimeout(timer);
  }, [text, displayedText, speed, enabled]);

  return { displayedText, isTyping };
}
