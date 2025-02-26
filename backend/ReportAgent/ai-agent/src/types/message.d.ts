type MessageComponent =
  | "options"
  | "training"
  | "trainingNFT"
  | "generate"
  | "claimRoyalty"
  | "buyLicenseToken"
  | "twit";

interface Message {
  content: string;
  isAnswer: boolean;
  isTyping?: boolean;
  fullContent?: string;
}

interface MessageWithLoading extends Message {
  isLoading?: boolean;
  component?: JSX.Element;
}
