import { FormEvent, useEffect, useState } from "react";
import styles from "./Chat.module.scss";
import { checkStatus, uploadTrainingImage } from "@/services/api.service";
import Link from "next/link";
import { useStoryClient } from "@/app/providers";
import { mintAndRegisterIpa } from "@/services/ipa.service";
import { typeMessage } from "@/utils/message";

interface TrainingCharacterImagesProps {
  setMessages: React.Dispatch<React.SetStateAction<MessageWithLoading[]>>;
  setIsAITyping: React.Dispatch<React.SetStateAction<boolean>>;
}

export default function TrainingCharacterImages({ 
  setMessages, 
  setIsAITyping 
}: TrainingCharacterImagesProps) {
  const { client } = useStoryClient();
  const [characterName, setCharacterName] = useState("");
  const [characterImage, setCharacterImage] = useState<File | null>(null);
  const [formError, setFormError] = useState(false);
  const [isTraining, setIsTraining] = useState(false);
  const [taskId, setTaskId] = useState<string | null>(null);
  const [mediaUrl, setMediaUrl] = useState<string | null>(null);
  const [progress, setProgress] = useState("");
  const [isSuccess, setIsSuccess] = useState(false);
  const [saveState, setSaveState] = useState(1);
  const [agentUrl, setAgentUrl] = useState("");

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();

    if (!characterName || !characterImage) {
      setFormError(true);
      return;
    }

    const formData = new FormData();
    formData.append("character_name", characterName);
    formData.append("character_image", characterImage);

    /** 성공하면 화면이 넘어가야 되긴 하지만 영상 촬영을 위해 바로 넘어가는 걸로 변경 -> 밑에 주석 부분 있음
     * [이후 수정]
     * - 넘어갈 동안 Loading으로 변경하기
     */
    setIsTraining(true);

    const responseData = await uploadTrainingImage(
      characterName,
      characterImage
    );
    console.log(responseData);

    /* uploadTrainingImage 시작하면 Training 시작을 알리고 화면 변경 */
    // if (responseData) {
    //   setIsTraining(true);
    // }

    if (responseData && responseData.task_id) {
      setTaskId(responseData.task_id);
    }
    if(responseData && responseData.media_url){
      setMediaUrl(responseData.media_url)
    }
  };

  useEffect(() => {
    const checkTrainingStatus = async () => {
      if (!taskId) return;

      try {
        const response = await checkStatus(taskId);
        console.log(response.logs);

        /**
         * Training 횟수 원래는 1500이여야한다. 밑에는 테스트로 800으로 줄인거다.
         * 1. 1499가 되면 saveState 2로변경
         * 2. saveState가 2이면 isSuccess가 ture가되고 progress 100으로 유지
         */
        // if (response.logs.includes("1499/1500")) {
        //   setSaveState(2);
        // }
        // if (response.logs.includes("99/100")) {
          // setSaveState(2);
        // }

        // if (saveState === 2) {
          // if (response.logs.includes("Saved to")) {
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
        // }

        /**
         * [이후 수정]
         * - training될 때 `${characterName}_flux_lora_v1:`가 아니면 다 Loding으로 처리 되어 있다.
         * - 처음 `${characterName}_flux_lora_v1:`나오기 전에 Loding으로 처리
         * - `${characterName}_flux_lora_v1:`나오면 progress에 값을 넣기
         * - generating images라는 문구가 중간에 나올때 기존 progress값 유지
         */
        const pattern = new RegExp(`${characterName}_flux_lora_v1:\\s*(\\d+)%`);
        const match = response.logs.match(pattern);
        setProgress(match ? match[1] : progress);
      } catch (error) {
        console.error("Status check failed:", error);
      }
    };

    checkTrainingStatus();
    const intervalId = setInterval(checkTrainingStatus, 5000);

    return () => clearInterval(intervalId);
  }, [taskId, characterName, saveState]);

  return (
    <>
      {isTraining ? (
        <div className={styles.status_container}>
          <p className={styles.text}>Training {characterName} character</p>
          {progress ? (
            <p className={styles.progress}>{progress}%</p>
          ) : (
            <div className={styles.spinner_wrap}>
              <div className={styles.spinner}></div>
            </div>
          )}

          {isSuccess && (
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
                    await mintAndRegisterIpa(client, mediaUrl, true, agentUrl, characterName);

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
        <div className={styles.training_form_container}>
          <p>To start the LoRA model training, please follow these steps:</p>
          <ol>
            <li>1. Enter your character name</li>
            <li>2. Upload your character image</li>
          </ol>

          <form onSubmit={handleSubmit}>
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
            <div className={styles.form_group}>
              <label>Character Image:</label>
              <div className={styles.file_input_wrapper}>
                <input
                  type="file"
                  id="characterImage"
                  name="character_image"
                  accept="image/*"
                  required
                  className={styles.hidden_input}
                  onChange={(e) =>
                    setCharacterImage(e.target.files?.[0] || null)
                  }
                />
                <label
                  htmlFor="characterImage"
                  className={styles.custom_file_button}
                >
                  <span>Choose File</span>
                </label>
                <span className={styles.file_name}>
                  {characterImage ? characterImage.name : "No file chosen"}
                </span>
              </div>
            </div>

            {formError && (
              <p className={styles.error_message}>
                Please fill in all required fields
              </p>
            )}
            <button type="submit" className={styles.btn}>
              Start Training
            </button>
          </form>
        </div>
      )}
    </>
  );
}
