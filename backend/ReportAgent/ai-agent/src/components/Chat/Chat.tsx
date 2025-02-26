"use client";

import {
  ChangeEvent,
  useState,
  FormEvent,
  KeyboardEvent,
  useRef,
  useEffect,
} from "react";
import styles from "./Chat.module.scss";
import { Button } from "@/components/common/Button/Button";
import { useAccount } from "wagmi";

interface ChatProps {
  onSendMessage: (message: string) => void;
  isDisabled?: boolean;
  optionText?: string;
  addNewStartOption: () => void;
}

export function Chat({
  onSendMessage,
  isDisabled = false,
  optionText,
  addNewStartOption,
}: ChatProps) {
  const [input, setInput] = useState("");
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const { isConnected } = useAccount();

  useEffect(() => {
    if (optionText) {
      setInput(optionText);
    }
  }, [optionText]);

  const resetTextareaHeight = () => {
    if (textareaRef.current) {
      textareaRef.current.style.height = "40px";
    }
  };

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault();
    if (input.trim() && !isDisabled && isConnected) {
      onSendMessage(input);
      setInput("");
      resetTextareaHeight();
    }
  };

  const handleInput = (e: ChangeEvent<HTMLTextAreaElement>) => {
    if (!isConnected) return; // 로그인하지 않은 상태에서는 입력 무시

    setInput(e.target.value);
    e.target.style.height = "40px";
    const scrollHeight = e.target.scrollHeight;
    e.target.style.height = scrollHeight > 200 ? "200px" : `${scrollHeight}px`;
  };

  const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey && !isDisabled && isConnected) {
      e.preventDefault();
      handleSubmit(e);
    }
  };

  return (
    <>
      <div className={styles.input_container}>
        {isConnected && (
          <div className={styles.help_btns}>
            <Button content="help options 👋" onClick={addNewStartOption} />
          </div>
        )}
        <form onSubmit={handleSubmit}>
          <textarea
            ref={textareaRef}
            value={input}
            onChange={handleInput}
            onKeyDown={handleKeyDown}
            placeholder={
              isConnected
                ? "Send a message..."
                : "Please login to chat with AI Agent"
            }
            className={`${styles.input} ${!isConnected ? styles.disabled : ""}`}
            rows={1}
            disabled={!isConnected}
          />

          <Button
            type="C"
            content="Send"
            onClick={handleSubmit}
            disabled={isDisabled || !input.trim() || !isConnected}
          />
        </form>
      </div>
    </>
  );
}
