import styles from "./Chat.module.scss";
import { useState, useEffect, Dispatch, SetStateAction } from "react";
import {
  fetchAssets,
  getMetadataFromIpAsset,
  getLicenseTokenListFromIpAsset,
  getLicenseIdFromIpAsset
} from "@/utils/fetchIpaAssets";
import { Button } from "../common/Button/Button";
import { twitToTakoyanAi } from "@/services/api.service";
import { typeMessage } from "@/utils/message";
import { useAccount } from "wagmi";

interface TwitToTakoyanAiProp {
  setMessages: Dispatch<SetStateAction<MessageWithLoading[]>>;
  setIsAITyping: Dispatch<SetStateAction<boolean>>;
  addLoadingMessage?: () => void;
  replaceLoadingWithComponent?: (componentType: string) => void;
}

export default function TwitToTakoyanAi({
  setMessages,
  setIsAITyping,
  addLoadingMessage,
  replaceLoadingWithComponent
}: TwitToTakoyanAiProp) {
  const { address } = useAccount();
  const [ipaFilters, setIpaFilters] = useState([]);
  const [loading, setLoading] = useState(true);
  const [twitterHandle, setTwitterHandle] = useState("");
  const [twitMessage, setTwitMessage] = useState("");
  const [buttonStatus, setButtonStatus] = useState(""); //"", loading, done
  const [selectFilter, setSelectFilter] = useState("");
  const [agentUrl, setAgentUrl] = useState("");
  const [ipId, setIpId] = useState("");
  const [licenseTermsId, setLicenseTermsId] = useState("");

  useEffect(() => {
    const getIpaAssets = async () => {
      try {
        setLoading(true);
        const assetsData = await fetchAssets();

        if (
          !assetsData ||
          !assetsData.data ||
          !Array.isArray(assetsData.data)
        ) {
          console.error("유효하지 않은 assetsData 형식:", assetsData);
          setIpaFilters([]);
          return;
        }

        // 유효한 토큰 URI가 있는 에셋만 필터링
        const validAssets = assetsData.data.filter(
          (asset) =>
            asset &&
            asset.nftMetadata &&
            asset.nftMetadata.tokenUri &&
            asset.nftMetadata.tokenUri.includes("https://ipfs.io/")
        );

        // 메타데이터를 가져와서 필터링하는 Promise 배열 생성
        const metadataPromises = validAssets.map(async (asset) => {
          try {
            const metadata = await getMetadataFromIpAsset(
              asset.nftMetadata.tokenUri
            );
            // 유효한 메타데이터가 있고, name이 "Playarts AI Agent"인 경우만 반환
            if (metadata && metadata.description.includes("AI Agent")) {
              return {
                ...asset,
                metadata,
              };
            }
            return null;
          } catch (e) {
            return null;
          }
        });

        // Promise.allSettled를 사용하여 오류가 있는 Promise도 처리
        const results = await Promise.allSettled(metadataPromises);

        // 성공한 결과만 필터링하고 null이 아닌 값만 추출
        const filteredIpas = results
          .filter(
            (result) => result.status === "fulfilled" && result.value !== null
          )
          .map((result) => (result as PromiseFulfilledResult<any>).value);
        setIpaFilters(filteredIpas);
      } catch (error) {
        console.error("IPA 에셋 로딩 실패:", error);
        setIpaFilters([]);
      } finally {
        setLoading(false);
      }
    };

    getIpaAssets();
  }, []);

  const handleIpaFilterClick = async (ipa) => {
    try {
      const ipaName = ipa.metadata?.name || "IPA";
      const externalUrl = ipa.metadata.external_url;
      setSelectFilter(ipaName);
      setAgentUrl(externalUrl);
      setIpId(ipa.ipId);

      // 라이선스 ID 가져오기
      const licenseData = await getLicenseIdFromIpAsset(ipa.ipId);
      if (licenseData?.data?.[0]?.licenseTermsId) {
        setLicenseTermsId(licenseData.data[0].licenseTermsId);
      } else {
        console.warn("라이선스 ID를 찾을 수 없습니다");
      }
    } catch (error) {
      console.error("IPA 필터 클릭 처리 오류:", error);
    }
  };

  async function handleTwit() {
    setButtonStatus('loading');
    try {
      // 라이선스 토큰이 있는지 체크
      if (!ipId) {
        console.error("IP ID가 설정되지 않았습니다");
        setButtonStatus("");
        return;
      }

      const ipList = await getLicenseTokenListFromIpAsset(ipId);
      const hasLicenseToken = ipList?.data?.find((x) => x.owner === address);
      
      if (!hasLicenseToken) {
        // 토큰 없으면?
        console.log("라이선스 토큰이 없습니다. 구매 화면으로 이동합니다.");
        setButtonStatus("");
        
        if (ipId && licenseTermsId && addLoadingMessage && replaceLoadingWithComponent) {
          // 메시지 UI에서 현재 로딩 제거 및 구매 화면으로 전환
          addLoadingMessage();
          replaceLoadingWithComponent("buyLicenseToken");
        } else {
          // 필요한 ID 값이 없는 경우 또는 함수가 없는 경우 처리
          console.error("라이선스 구매 화면으로 이동할 수 없습니다");
          typeMessage("라이선스 토큰이 필요합니다. 먼저 라이선스를 구매해 주세요.", setMessages, setIsAITyping);
        }
        return;
      }
      
      // 라이선스 토큰이 있으면 트윗 진행
      const regex = /\/agent\/([0-9a-f-]+)\/inference/;
      const match = agentUrl.match(regex);
      let agentKey = "";
      if (match && match[1]) {
        agentKey = match[1];
      }
      
      const result = await twitToTakoyanAi(agentKey, selectFilter, twitMessage, twitterHandle);
      if (result.response) {
        const twitterUrl = `[View on Twitter](${result.twitterUrl})`;
        const imgMessage = `![Generated Image](${result.imageUrl})`;
        const fullMessage = `${twitterUrl}\n\n${imgMessage}\n\n`;
        typeMessage(fullMessage, setMessages, setIsAITyping);
        setButtonStatus("done");
      }
    } catch (error) {
      console.error(error);
      setButtonStatus("");
      
      // 에러 메시지 표시
      typeMessage("트윗 생성 중 오류가 발생했습니다. 다시 시도해 주세요.", setMessages, setIsAITyping);
    }
  }

  return (
    <div className={styles.filter_container}>
      <div className={styles.filter_list_container}>
        <h1>Twit to takoyan AI</h1>
        {loading ? (
          <div className={styles.spinner_wrap}>
            <div className={styles.spinner}></div>
          </div>
        ) : ipaFilters.length > 0 ? (
          <ul>
            {ipaFilters.map((ipa, index) => (
              <li
                key={index}
                className={`${
                  selectFilter === ipa.metadata?.name ? styles.selected : ""
                }`}
                onClick={() => handleIpaFilterClick(ipa)}
              >
                {ipa.metadata?.image ? (
                  <img
                    src={ipa.metadata.image}
                    alt={ipa.metadata.name || `IPA ${index}`}
                    onError={(e) => {
                      const target = e.target as HTMLImageElement;
                      target.src = "/images/favicon.png";
                      target.style.filter = "grayscale(100%)";
                      target.style.backgroundColor = "#c3c3c3";
                      target.style.opacity = "0.8";
                    }}
                  />
                ) : (
                  <div className={styles.placeholder_image}></div>
                )}
                <p>{ipa.metadata?.name || `IPA ${index}`}</p>
              </li>
            ))}
          </ul>
        ) : (
          <p className={styles.empty_message}>There is no IPA filter yet.</p>
        )}
        <div className={styles.twit_handle_area}>
            <label htmlFor="twitHandle">Enter Twitter @handle</label>
            <input
                name="twitHandle"
                type="text"
                placeholder="X(twitter) @handle"
                value={twitterHandle}
                onChange={(e) => setTwitterHandle(e.target.value)}
            />
            <label htmlFor="twitMessage">Enter message</label>
            <input
                name="twitMessage"
                type="text"
                placeholder="Write down anything you want"
                value={twitMessage}
                onChange={(e) => setTwitMessage(e.target.value)}
            />
            <Button
                type="A"
                content={buttonStatus == "done" ? "Done!" : "Twit!"}
                onClick={handleTwit}
                loading={buttonStatus == "loading"}
                disabled={buttonStatus == "loading" || buttonStatus == "done" || !selectFilter}
            />
        </div>
      </div>
    </div>
  );
}