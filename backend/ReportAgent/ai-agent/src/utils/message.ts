// src/utils/typeMessage.ts

import { Dispatch, SetStateAction } from "react";

export const typeMessage = (
  fullContent: string,
  setMessages: Dispatch<SetStateAction<Message[]>>,
  setIsAITyping: Dispatch<SetStateAction<boolean>>,
  speed: number = 10
) => {
  if(!fullContent) return;
  let currentIndex = 0;
  setIsAITyping(true);

  setMessages((prev) => [
    ...prev,
    {
      content: "",
      isAnswer: true,
      isTyping: true,
      fullContent,
    },
  ]);

  const intervalId = setInterval(() => {
    setMessages((prev) => {
      const lastMessage = prev[prev.length - 1];
      if (!lastMessage.isTyping) return prev;

      currentIndex++;
      if (currentIndex >= fullContent.length) {
        clearInterval(intervalId);
        setIsAITyping(false);
        return prev.map((msg, idx) =>
          idx === prev.length - 1
            ? { ...msg, content: fullContent, isTyping: false }
            : msg
        );
      }

      return prev.map((msg, idx) =>
        idx === prev.length - 1
          ? { ...msg, content: fullContent.slice(0, currentIndex) }
          : msg
      );
    });
  }, speed);

  return intervalId;
};

// Markdown 이미지 문법에서 URL 추출을 위한 정규식
export const extractImageUrl = (content: string) => {
  const regex = /\!\[.*?\]\((.*?)\)/;
  const match = content.match(regex);
  return match ? match[1] : null;
};
