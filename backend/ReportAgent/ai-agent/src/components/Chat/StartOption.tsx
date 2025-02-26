import { aiAgentOptions } from "@/constants/aiAgentOption";
import styles from "./Chat.module.scss";
import { Dispatch, SetStateAction } from "react";
import { useAccount } from "wagmi";

interface OptionProps {
  setOption: Dispatch<SetStateAction<string>>;
}
export function StartOption({ setOption }: OptionProps) {
  const { isConnected } = useAccount();

  const handleOptionClick = (optionType: string) => {
    if (!isConnected) {
      alert("Please login to chat with AI Agent");
      return;
    }

    setOption(optionType);
  };

  return (
    <div className={styles.start_ption_container}>
      <h1>
        Welcome to PlayArts AI Assistant!
        <br />I can help you with:
      </h1>

      <ul>
        {aiAgentOptions.map((option) => (
          <li key={option.type} onClick={() => handleOptionClick(option.type)}>
            <p>{option.title}</p>
          </li>
        ))}
      </ul>

      <p>What would you like to do?</p>
    </div>
  );
}
