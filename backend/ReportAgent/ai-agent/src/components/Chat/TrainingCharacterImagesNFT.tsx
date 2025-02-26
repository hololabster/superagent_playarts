import { FormEvent, useEffect, useState } from "react";
import styles from "./Chat.module.scss";
import { useAccount } from "wagmi";
import { truncateText } from "@/utils/text";
import {
  fetchNFTs,
  uploadTrainingImage,
  checkStatus,
} from "@/services/api.service";
import Link from "next/link";
import { useStoryClient } from "@/app/providers";
import { mintAndRegisterIpa } from "@/services/ipa.service";
import { typeMessage } from "@/utils/message";

interface NFT {
  token_id: string;
  name: string;
  image_url: string;
  token_uri: string;
}
interface TrainingCharacterImagesProps {
  setMessages: React.Dispatch<React.SetStateAction<MessageWithLoading[]>>;
  setIsAITyping: React.Dispatch<React.SetStateAction<boolean>>;
}
export default function TrainingCharacterImagesNFT({ 
  setMessages, 
  setIsAITyping 
}: TrainingCharacterImagesProps) {
  const { client } = useStoryClient();
  const { address } = useAccount();
  const [nfts, setNfts] = useState<NFT[] | null>(null);
  const [characterName, setCharacterName] = useState("");
  const [trainingStep, setTrainingStep] = useState(0); // 1: 성공, 2: nfts데이터 있을 경우
  const [selectedNft, setSelectedNft] = useState<string | null>(null);
  const [errorMessage, setErrorMessage] = useState("");
  const [isTraining, setIsTraining] = useState(false);
  const [taskId, setTaskId] = useState<string | null>(null);
  const [progress, setProgress] = useState("");
  const [isSuccess, setIsSuccess] = useState(false);
  const [saveState, setSaveState] = useState(1); // 1: training... 2: 1499일때(즉 완료시)
  const [isLoading, setIsLoading] = useState(false);
  const [isTrainingLoading, setIsTrainingLoading] = useState(true); // training전용 loading useEffect에서 사용되기 때문에 처음부터 true로 변경
  const [agentUrl, setAgentUrl] = useState("");

  const handleSearchNFTsSubmit = async (e: FormEvent) => {
    e.preventDefault();

    if (!address) return;

    setIsLoading(true);
    const responseData = await fetchNFTs(address);
    console.log(responseData);

    if (responseData && responseData.status === "success") {
      setTrainingStep(1);
      setIsLoading(false);

      if (responseData.nfts.length > 0) {
        setNfts(responseData.nfts);
        setTrainingStep(2);
      }
    } else {
      setNfts([]);
    }
  };

  // image url -> File
  const urlToFile = async (imageUrl: string) => {
    try {
      const response = await fetch(imageUrl);
      const blob = await response.blob();
      const contentType = response.headers.get("content-type") || "image/jpeg";
      const extension = contentType.split("/")[1] || "jpg";
      const randomFileName = `image_${Date.now()}_${Math.random()
        .toString(36)
        .substring(2, 15)}.${extension}`;
      const file = new File([blob], randomFileName, { type: contentType });

      return file;
    } catch (error) {
      console.error("Error converting URL to File:", error);
      throw error;
    }
  };

  const handleTrainingImageSubmit = async (e: FormEvent) => {
    e.preventDefault();

    if (!characterName || !selectedNft) {
      setErrorMessage(
        "Please enter a character name and select an NFT from the gallery"
      );
      return;
    }

    setIsLoading(true);

    const formData = new FormData();
    formData.append("character_name", characterName);
    formData.append("character_image", await urlToFile(selectedNft));

    const imageFile = await urlToFile(selectedNft);
    console.log(imageFile);

    const responseData = await uploadTrainingImage(characterName, imageFile);
    console.log(responseData);

    if (responseData) {
      setIsTraining(true);
      setIsLoading(false);
    }

    if (responseData && responseData.task_id) {
      setTaskId(responseData.task_id);
    }
  };

  useEffect(() => {
    const checkTrainingStatus = async () => {
      if (!taskId) return;

      try {
        const response = await checkStatus(taskId);
        console.log(response.logs);

        /**
         * Training 횟수 1500, ("1499/1500" or "799/800")
         * 1. 1499가 되면 saveState 2로변경
         * 2. saveState가 2이면 isSuccess가 ture가되고 progress 100으로 유지
         */
        if (response.logs.includes("Training completed")) {
          setSaveState(2);
          const match = response.logs.match(/https:\/\/.*?inference/);
          const extractedUrl = match ? match[0] : "http://211.175.242.13:7860/";
          setProgress("100");
          setIsSuccess(true);
          setAgentUrl(extractedUrl);
          clearInterval(intervalId);
          return;
        }

        const pattern = new RegExp(`${characterName}_flux_lora_v1:\\s*(\\d+)%`);
        const match = response.logs.match(pattern);
        const newProgress = match ? match[1] : progress;
        setProgress(newProgress);

        if (newProgress !== "") {
          setIsTrainingLoading(false);
        }
      } catch (error) {
        console.error("Status check failed:", error);
      }
    };

    checkTrainingStatus();
    const intervalId = setInterval(checkTrainingStatus, 5000);

    return () => clearInterval(intervalId);
  }, [taskId, characterName, saveState]);

  return (
    <div className={styles.training_form_container}>
      <h1>Search NFT</h1>
      {/* 1. NFT 검색 -> 로그인한 지갑주소 고정 */}
      <div className={styles.search_nft_container}>
        <form onSubmit={handleSearchNFTsSubmit}>
          <div className={styles.form_group}>
            <label htmlFor="WalletAddress">NFT Wallet Address:</label>
            <input
              type="text"
              name="wallet_address"
              required
              className={styles.form_control}
              value={address}
              readOnly
            />
          </div>

          {trainingStep < 1 && (
            <button type="submit" className={styles.btn}>
              Search NFT
            </button>
          )}

          {trainingStep === 0 && isLoading && (
            <div className={styles.spinner_wrap}>
              <div className={styles.spinner}></div>
            </div>
          )}
          {trainingStep > 1 && (
            <div className={styles.nft_gallery}>
              <p className={styles.title}>NFT Gallery:</p>
              {nfts && nfts.length > 0 ? (
                <ul>
                  {nfts.map((nft) => (
                    <li
                      key={nft.name}
                      onClick={() => window.open(nft.image_url, "_blank")}
                    >
                      <img src={nft.image_url} alt={nft.token_id} />

                      <p className={styles.nft_name}>
                        {nft.name.includes(" ")
                          ? nft.name.split(" ")[0]
                          : nft.name}
                      </p>
                      <p className={styles.nft_mint_req}>
                        {truncateText(nft.token_id)}
                      </p>
                    </li>
                  ))}
                </ul>
              ) : (
                <p className={styles.empty_message}>
                  No NFTs found in this wallet
                </p>
              )}
            </div>
          )}
        </form>
      </div>

      {/* 2. NFT 학습 폼 제출, 3. Training... 4. successful training */}
      {trainingStep === 2 && (
        <div className={styles.upload_training_container}>
          {isTraining ? (
            // 3. Training...
            <div className={styles.status_container}>
              <p className={styles.text}>Training {characterName} character</p>

              {isTrainingLoading ? (
                <div className={styles.spinner_wrap}>
                  <div className={styles.spinner}></div>
                </div>
              ) : (
                <p className={styles.progress}>{progress}%</p>
              )}

              {isSuccess && (
                // 4. successful training
                <div className={styles.success_container}>
                  <p>Training completed successfully 😘</p>
                  <Link
                    href={agentUrl}
                    className={styles.url_text}
                  >
                    move to agent 🤖
                  </Link>
                  <button
              className={styles.mintButton}
              onClick={async () => {
                if (client) {
                  setMessages((prev) => [
                    ...prev,
                    { content: "Mint and Register IPA", isAnswer: false },
                  ]);
                  setMessages((prev) => [
                    ...prev,
                    {
                      content: "",
                      isAnswer: true,
                      isLoading: true,
                    },
                  ]);
                  const { txHash, ipId, licenseTermsIds } =
                    await mintAndRegisterIpa(client, selectedNft, true, agentUrl, characterName);

                  setMessages((prev) => prev.slice(0, -1));
                  const message = `Root IPA created at transaction hash: ${txHash}
                  IPA ID: ${ipId}
                  License Terms ID: ${licenseTermsIds[0]}
                  View on the explorer: https://aeneid.explorer.story.foundation/ipa/${ipId}`;
                  typeMessage(message, setMessages, setIsAITyping);
                }
              }}
              title="Mint and Register IPA"
            >
              Mint and Register IPA
            </button>
                </div>
              )}
            </div>
          ) : (
            // 2. NFT 학습 폼 제출
            <>
              <h1>Train via NFT</h1>
              <form onSubmit={handleTrainingImageSubmit}>
                <div className={styles.form_group}>
                  <label htmlFor="characterName">Character Name:</label>
                  <input
                    type="text"
                    name="character_name"
                    required
                    placeholder="Enter character name"
                    className={styles.form_control}
                    value={characterName}
                    onChange={(e) => setCharacterName(e.target.value)}
                  />
                </div>
                <div className={`${styles.nft_gallery} ${styles.image_wrap}`}>
                  <p className={styles.title}>Character Image:</p>
                  <ul>
                    {nfts &&
                      nfts.map((nft) => (
                        <li
                          key={nft.name}
                          onClick={() => setSelectedNft(nft.image_url)}
                          className={
                            selectedNft === nft.image_url ? styles.selected : ""
                          }
                        >
                          <img src={nft.image_url} alt={nft.token_id} />
                        </li>
                      ))}
                  </ul>
                </div>

                <p className={styles.error_message}>{errorMessage}</p>

                <button type="submit" className={styles.btn}>
                  Start Training with Selected NFT
                </button>
              </form>
              {trainingStep === 2 && isLoading && (
                <div className={styles.spinner_wrap}>
                  <div className={styles.spinner}></div>
                </div>
              )}
            </>
          )}
        </div>
      )}
    </div>
  );
}
