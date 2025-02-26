import { imageFilters } from "@/constants/artwork";
import styles from "./Chat.module.scss";
import Image from "next/image";
import { Dispatch, SetStateAction, useState, useEffect } from "react";
import {
  fetchAssets,
  getLicenseIdFromIpAsset,
  getMetadataFromIpAsset,
} from "@/utils/fetchIpaAssets";

interface FilterOtionProp {
  selectFilter: string;
  setSelectFilter: Dispatch<SetStateAction<string>>;
  setInputText: Dispatch<SetStateAction<string>>;
  setIpId: Dispatch<SetStateAction<string>>;
  setLicenseTermsId: Dispatch<SetStateAction<string>>;
  setExternalUrl: Dispatch<SetStateAction<string>>;
}

export default function FilterOption({
  selectFilter,
  setSelectFilter,
  setInputText,
  setIpId,
  setLicenseTermsId,
  setExternalUrl,
}: FilterOtionProp) {
  const [ipaFilters, setIpaFilters] = useState([]);
  const [loading, setLoading] = useState(true);

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
        console.log(filteredIpas);
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

  const handleFilterClick = (filterName: string) => {
    if (selectFilter === filterName) {
      setSelectFilter("");
      setInputText("Please Generate image");
    } else {
      setSelectFilter(filterName);
      setInputText(`Please Generate image of "${filterName}"`);
    }
  };

  const handleIpaFilterClick = async (ipa) => {
    const ipaName = ipa.metadata?.name || "IPA";
    const licenseData = await getLicenseIdFromIpAsset(ipa.ipId);
    const licenseTermsId = licenseData?.data?.[0]?.licenseTermsId;
    if (!licenseTermsId) {
      console.error("License terms ID not found");
      return; // 또는 오류 처리
    }
    const externalUrl = ipa.metadata?.external_url
      ? ipa.metadata.external_url
      : "";
    setSelectFilter(ipaName);
    setIpId(ipa.ipId);
    setLicenseTermsId(licenseTermsId);
    setExternalUrl(externalUrl);
    setInputText(`Please Generate image with IPA "${ipaName}"`);
  };

  return (
    <div className={styles.filter_container}>
      <div className={styles.filter_list_container}>
        <h1>filter</h1>
        <ul>
          {imageFilters.map((filter) => (
            <li
              key={filter.name}
              className={`${
                selectFilter === filter.name ? styles.selected : ""
              }`}
              onClick={() => handleFilterClick(filter.name)}
            >
              <Image
                src={filter.imageUrl}
                alt={filter.name}
                width={32}
                height={32}
              />
              <p>{filter.name}</p>
            </li>
          ))}
        </ul>
      </div>

      <div className={styles.filter_list_container}>
        <h1>IPA filter</h1>
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
      </div>
    </div>
  );
}
