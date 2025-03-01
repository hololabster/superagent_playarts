"use client";

import { Chat } from "@/components/Chat/Chat";
import styles from "./page.module.scss";
import { useAside } from "@/context/AsideContext";
import React, { useState, useEffect, useRef, useCallback } from "react";
import { typeMessage, extractImageUrl } from "@/utils/message";
import ReactMarkdown from "react-markdown";
import html2pdf from "html2pdf.js";
import { Download } from "lucide-react";
import { generateWithIpa, sendMessage } from "@/services/api.service";
import { StartOption } from "@/components/Chat/StartOption";
import { useAccount, useChainId, useChains } from "wagmi";
import FilterOption from "@/components/Chat/FilterOption";
import TrainingCharacterImages from "@/components/Chat/TrainingCharacterImages";
import TrainingCharacterImagesNFT from "@/components/Chat/TrainingCharacterImagesNFT";
import { mintAndRegisterIpa } from "@/services/ipa.service";
import { useStoryClient } from "./providers";
import { getLicenseTokenListFromIpAsset } from "@/utils/fetchIpaAssets";
import BuyLicenseToken from "@/components/Chat/BuyLicenseToken";
import ClaimRoyalty from "@/components/Chat/ClaimRoyalty";
import TwitToTakoyanAi from "@/components/Chat/TwitToTakoyanAi";
import OutfitEditor from "@/components/Chat/OutfitEditor";

export default function Home() {
  const { client } = useStoryClient();
  const { isAsideOpen } = useAside();
  const initializeRef = useRef(false);
  const [messages, setMessages] = useState<MessageWithLoading[]>([]);
  const [isAITyping, setIsAITyping] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const messageRefs = useRef<Array<HTMLDivElement | null>>([]);
  const { address } = useAccount();
  const [option, setOption] = useState("");
  const [inputText, setInputText] = useState("");
  const [selectFilter, setSelectFilter] = useState("");
  const [selectedIpId, setSelectedIpId] = useState("");
  const [licenseTermsId, setLicenseTermsId] = useState("");
  const [externalUrl, setExternalUrl] = useState("");
  // const chainId = useChainId();
  // const chains = useChains();

  // console.log(chainId, chains);
  // const chainName =
  //   chains.find((chain) => chain.id === chainId)?.name || "Unknown Chain";
  // console.log(chainName);

  // isAnswer에 사용되는 컴포넌트
  const getComponentMap = () => {
    const componentMap: Record<MessageComponent, JSX.Element> = {
      options: <StartOption setOption={setOption} />,
      training: (
        <TrainingCharacterImages
          setMessages={setMessages}
          setIsAITyping={setIsAITyping}
        />
      ),
      trainingNFT: (
        <TrainingCharacterImagesNFT
          setMessages={setMessages}
          setIsAITyping={setIsAITyping}
        />
      ),
      generate: (
        <FilterOption
          selectFilter={selectFilter}
          setSelectFilter={setSelectFilter}
          setInputText={setInputText}
          setIpId={setSelectedIpId}
          setLicenseTermsId={setLicenseTermsId}
          setExternalUrl={setExternalUrl}
        />
      ),
      buyLicenseToken: (
        <BuyLicenseToken
          ipId={selectedIpId}
          licenseTermsId={licenseTermsId}
          setMessages={setMessages}
          setIsAITyping={setIsAITyping}
        />
      ),
      claimRoyalty: <ClaimRoyalty />,
      twit: (
        <TwitToTakoyanAi
          setMessages={setMessages}
          setIsAITyping={setIsAITyping}
          addLoadingMessage={addLoadingMessage}
          replaceLoadingWithComponent={replaceLoadingWithComponent}
        />
      ),
      outfit: (
        <OutfitEditor/>
      )
    };
    return componentMap;
  };

  // 선택한 타입에 알맞게 messages state에 추가
  const addNewComponent = useCallback(
    (type: MessageComponent) => () => {
      const componentMap = getComponentMap();
      setMessages((prev) => [
        ...prev,
        {
          content: "",
          isAnswer: true,
          component: componentMap[type],
        },
      ]);
    },
    []
  );

  // 초기 화면
  useEffect(() => {
    if (!initializeRef.current) {
      addNewComponent("options")();
      initializeRef.current = true;
    }
  }, []);

  // message 생성시 스크롤 맨 밑으로
  const scrollToBottom = useCallback(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, []);
  useEffect(() => {
    scrollToBottom();
    messageRefs.current = messageRefs.current.slice(0, messages.length);
  }, [messages, scrollToBottom]);

  // PDF, 이미지 다운로드
  const handleDownloadPDF = async (index: number) => {
    const messageEl = messageRefs.current[index];
    if (!messageEl) return;

    const opt = {
      margin: 1,
      filename: "ai-response.pdf",
      image: { type: "jpeg", quality: 0.98 },
      html2canvas: { scale: 2 },
      jsPDF: { unit: "in", format: "letter", orientation: "portrait" },
    };

    try {
      await html2pdf().set(opt).from(messageEl).save();
    } catch (error) {
      console.error("PDF generation failed:", error);
    }
  };
  const handleImageDownload = async (imageUrl: string) => {
    try {
      const response = await fetch(imageUrl);
      const blob = await response.blob();
      const objectUrl = URL.createObjectURL(blob);

      const link = document.createElement("a");
      link.href = objectUrl;
      link.download = "generated-image.png";
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      URL.revokeObjectURL(objectUrl);
    } catch (error) {
      console.error("Image download failed:", error);
    }
  };

  // 로딩 메시지 추가
  const addLoadingMessage = useCallback(() => {
    setMessages((prev) => [
      ...prev,
      {
        content: "",
        isAnswer: true,
        isLoading: true,
      },
    ]);
  }, []);

  // 마지막 메시지(Loading) 제거 후 컴포넌트 추가
  const replaceLoadingWithComponent = useCallback(
    (componentType: MessageComponent) => {
      setTimeout(() => {
        setMessages((prev) => {
          const newMessages = [...prev];
          newMessages.pop(); // 로딩 메시지 제거
          const componentMap = getComponentMap();
          const component = componentMap[componentType];

          return [
            ...newMessages,
            {
              content: "",
              isAnswer: true,
              component,
            },
          ];
        });
      }, 1500);
    },
    [selectedIpId, licenseTermsId]
  );

  // 사용자 메시지 추가
  const addUserMessage = useCallback((content: string) => {
    setMessages((prev) => [...prev, { content, isAnswer: false }]);
  }, []);

  // 메시지 전송 + "Training character images", "Training character images NFT" 텍스트 입력할 경우
  const handleSendMessage = async (message: string) => {
    addUserMessage(message);
    addLoadingMessage();

    // 메시지 전송 전 체크
    const isGeneratingWithIpa = message.includes("Generate image with IPA");

    if (isGeneratingWithIpa) {
      // 라이선스 토큰이 있는지 체크
      const ipList = await getLicenseTokenListFromIpAsset(selectedIpId);
      const hasLicenseToken = ipList?.data?.find((x) => x.owner === address);
      if (!hasLicenseToken) {
        // 토큰 없으면?
        if (selectedIpId && licenseTermsId) {
          setMessages((prev) => prev.slice(0, -1));
          addLoadingMessage();
          replaceLoadingWithComponent("buyLicenseToken");
        } else {
          // 필요한 ID 값이 없는 경우 처리
          console.error("Missing ipId or licenseTermsId");
          // 사용자에게 알리는 메시지 추가
        }
        return false;
      }
    }

    let responseData;
    // 메시지 전송 후
    if (isGeneratingWithIpa) {
      responseData = await generateWithIpa(message, externalUrl);
    } else {
      responseData = await sendMessage(message);
    }

    const isTraining =
      responseData.response &&
      responseData.response.includes("<form id='uploadTrainingForm'");

    const isTrainingNFT =
      responseData.response &&
      responseData.response.includes("<form id='nftTrainingForm'");

    if (isTraining) {
      setMessages((prev) => prev.slice(0, -1)); // 기존 로딩 메시지 제거
      addLoadingMessage();
      replaceLoadingWithComponent("training");
    } else if (isTrainingNFT) {
      setMessages((prev) => prev.slice(0, -1));
      addLoadingMessage();
      replaceLoadingWithComponent("trainingNFT");
    } else if (isGeneratingWithIpa) {
      // 유저의 Agent로 만들어진 이미지라는걸 표시해야함
      const response = `Generated image:\n\n![Generated Image](${responseData.image_url})`
      setMessages((prev) => prev.slice(0, -1));
      typeMessage(response, setMessages, setIsAITyping);
    } else {
      // 일반적인 응답 처리
      setMessages((prev) => prev.slice(0, -1));
      typeMessage(responseData.response, setMessages, setIsAITyping);
    }
  };

  // 메시지 렌더링
  const renderMessage = (message: MessageWithLoading, index: number) => {
    if (message.component) {
      return <>{message.component}</>;
    }

    if (message.isLoading) {
      return (
        <div className={styles.loading}>
          <span className={styles.dot}></span>
          <span className={styles.dot}></span>
          <span className={styles.dot}></span>
        </div>
      );
    }

    // AI응답 렌더링
    if (message.isAnswer) {
      const imageUrl = extractImageUrl(message.content);
      return (
        <div className={styles.messageContent}>
          <div className={styles.markdown}>
            <ReactMarkdown>{message.content}</ReactMarkdown>
            {message.isTyping && <span className={styles.cursor}>|</span>}
          </div>
          {!message.isTyping && (
            <button
              className={styles.downloadButton}
              onClick={() =>
                imageUrl
                  ? handleImageDownload(imageUrl)
                  : handleDownloadPDF(index)
              }
              title={imageUrl ? "Download Image" : "Download as PDF"}
            >
              <Download size={20} />
            </button>
          )}
          {!message.isTyping && imageUrl && (
            <button
              className={styles.mintButton}
              onClick={async () => {
                if (client) {
                  addUserMessage("Mint and Register IPA");
                  addLoadingMessage();
                  try {
                    const { txHash, ipId, licenseTermsIds } =
                    await mintAndRegisterIpa(client, imageUrl);

                    setMessages((prev) => prev.slice(0, -1));
                    const message = `Root IPA created at transaction hash: ${txHash}
                    IPA ID: ${ipId}
                    License Terms ID: ${licenseTermsIds[0]}
                    View on the explorer: https://aeneid.explorer.story.foundation/ipa/${ipId}`;
                    typeMessage(message, setMessages, setIsAITyping);
                  } catch (error) {
                    setMessages((prev) => prev.slice(0, -1));
                    const message = error.reason;
                    typeMessage(message, setMessages, setIsAITyping);
                  }
                }
              }}
              title="Mint and Register IPA"
            >
              Mint and Register IPA
            </button>
          )}
        </div>
      );
    }

    return (
      <>
        {message.content}
        {message.isTyping && <span className={styles.cursor}>|</span>}
      </>
    );
  };

  // 옵션 처리
  const handleOption = useCallback(
    (optionType: string) => {
      switch (optionType) {
        case "training":
          addUserMessage("Training character images");
          addLoadingMessage();
          replaceLoadingWithComponent("training");
          break;
        case "trainingNFT":
          addUserMessage("Training character images NFT");
          addLoadingMessage();
          replaceLoadingWithComponent("trainingNFT");
          break;
        case "analyzingNFT":
          setInputText("Analyzing NFT markets");
          break;
        case "analyzingWallet":
          setInputText(address ?? "");
          break;
        case "generate":
          addUserMessage("Generating images with filter name");
          addLoadingMessage();
          replaceLoadingWithComponent("generate");
          setInputText("Please Generate image");
          break;
        case "claim":
          addUserMessage("Do I have any royalties to claim?");
          addLoadingMessage();
          replaceLoadingWithComponent("claimRoyalty");
          break;
        case "twit":
          addLoadingMessage();
          replaceLoadingWithComponent("twit");
          break;
        case "outfit":
          addLoadingMessage();
          replaceLoadingWithComponent("outfit");
          break;
        default:
          break;
      }
    },
    [
      addUserMessage,
      addLoadingMessage,
      replaceLoadingWithComponent,
      address,
      setInputText,
    ]
  );

  // 옵션 변경 시 처리
  useEffect(() => {
    if (option) {
      handleOption(option);
      setOption("");
    }
  }, [option, handleOption]);

  return (
    <>
      <div className={styles.messages_container}>
        <div className={styles.messages}>
          {messages.map((message, index) => (
            <div
              key={index}
              ref={(el: HTMLDivElement | null) => {
                messageRefs.current[index] = el;
              }}
              className={`${styles.message} ${
                message.isAnswer ? styles.answer : "user"
              }`}
            >
              {renderMessage(message, index)}
            </div>
          ))}
          <div ref={messagesEndRef} />
        </div>
      </div>
      <div
        className={`${styles.chat_wrapper} ${
          isAsideOpen ? styles.open : styles.close
        }`}
      >
        <Chat
          onSendMessage={handleSendMessage}
          isDisabled={isAITyping}
          optionText={inputText}
          addNewStartOption={addNewComponent("options")}
        />
      </div>
    </>
  );
}
