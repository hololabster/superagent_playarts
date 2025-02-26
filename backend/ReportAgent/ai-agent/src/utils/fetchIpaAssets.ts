import { CONTRACT_ADDRESSES } from "@/constants/chains";

export const fetchAssets = async () => {
  try {
    const response = await fetch("https://api.storyapis.com/api/v3/assets", {
      method: "POST",
      headers: {
        "X-Api-Key": "MhBsxkU1z9fG6TofE59KqiiWV-YlYE8Q4awlLQehF3U",
        "X-Chain": "story-aeneid",
        accept: "application/json",
        "content-type": "application/json",
      },
      body: JSON.stringify({
        options: {
          tokenContractIds: [CONTRACT_ADDRESSES[1315]],
          pagination: {
            limit: 100,
          },
        },
      }),
    });

    const data = await response.json();
    return data;
  } catch (error) {
    console.error("에셋 가져오기 실패:", error);
    throw error;
  }
};

export const getMetadataFromIpAsset = async (metadataUri: string) => {
  if (!metadataUri) return;
  try {
    const response = await fetch(metadataUri, {
      method: "GET",
      headers: {
        accept: "application/json",
      },
    });

    const data = await response.json();
    return data;
  } catch (error) {
    console.error(`에셋 메타데이터 가져오기 실패 (${metadataUri}):`, error);
    throw error;
  }
};

export const getLicenseIdFromIpAsset = async (ipid: string) => {
  if (!ipid) return;
  try {
    const response = await fetch(
      `https://api.storyapis.com/api/v3/licenses/ip/terms/${ipid}`,
      {
        method: "GET",
        headers: {
          accept: "application/json",
          "X-Api-Key": "MhBsxkU1z9fG6TofE59KqiiWV-YlYE8Q4awlLQehF3U",
          "X-Chain": "story-aeneid",
        },
      }
    );

    const data = await response.json();
    return data;
  } catch (error) {
    console.error("에셋 라이선스 ID 가져오기 실패:", error);
  }
};

export const getLicenseTokenListFromIpAsset = async (ipid: string) => {
  if (!ipid) return;
  try {
    const response = await fetch(
      `https://api.storyapis.com/api/v3/licenses/tokens`,
      {
        method: "POST",
        headers: {
          accept: "application/json",
          "X-Api-Key": "MhBsxkU1z9fG6TofE59KqiiWV-YlYE8Q4awlLQehF3U",
          "X-Chain": "story-aeneid",
          "content-type": "application/json",
        },
        body: JSON.stringify({
          options: {
            where: {
              licensorIpId: ipid,
            },
          },
        }),
      }
    );

    const data = await response.json();
    return data;
  } catch (error) {
    console.error("에셋 라이선스 토큰 리스트 가져오기 실패:", error);
  }
};

//
export const getTransaction = async (txHash: string) => {
  if (!txHash) return;
  try {
    const response = await fetch(
      `https://api.storyapis.com/api/v3/transactions/${txHash}`,
      {
        method: "GET",
        headers: {
          accept: "application/json",
          "X-Api-Key": "MhBsxkU1z9fG6TofE59KqiiWV-YlYE8Q4awlLQehF3U",
          "X-Chain": "story-aeneid",
        },
      }
    );

    const data = await response.json();
    return data;
  } catch (error) {
    console.error("트랜잭션 정보 가져오기 실패:", error);
  }
};