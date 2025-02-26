import { useStoryClient } from "@/app/providers";
import { claimAllPossibleRevenue } from "@/services/ipa.service";
import { fetchAssets, getTransaction } from "@/utils/fetchIpaAssets";
import { useEffect, useRef, useState } from "react";
import { formatEther } from "viem";
import { useAccount } from "wagmi";

export default function ClaimRoyalty() {
  const { client } = useStoryClient();
  const { address } = useAccount();
  const [claimResult, setClaimResult] = useState<{
    claimedTokens?: any;
    success?: boolean;
    totalClaimed?: number;
  }>({});
  const [isLoading, setIsLoading] = useState(false);
  const [processedCount, setProcessedCount] = useState(0);
  const [totalCount, setTotalCount] = useState(0);
  const [ownAssetsCount, setOwnAssetsCount] = useState(0);
  const hasRunEffect = useRef(false);

  useEffect(() => {
    // 이미 실행된 경우 건너뛰기
    if (hasRunEffect.current || !address) return;
    const getIpaAssets = async () => {
      try {
        // 효과가 실행 중임을 표시
        hasRunEffect.current = true;
        setIsLoading(true);
        const assetsDataResponse = await fetchAssets();
        console.log("Fetched assets:", assetsDataResponse.data);
        
        if (!address) {
          console.error("User address not available");
          setIsLoading(false);
          return;
        }
        
        console.log("Current user address:", address);
        
        // Filter assets initiated by the current user
        const eligibleAssets = [];
        
        for (const asset of assetsDataResponse.data) {
          try {
            const txHash = asset.transactionHash;
            
            // Fetch transaction details
            const txData = await getTransaction(txHash);
            
            console.log(`Transaction for ${asset.ipId}:`, txData);
            
            // Check if the initiator is the current user
            if (txData.data && txData.data.initiator && 
                txData.data.initiator === address) {
              console.log(`Asset ${asset.ipId} was initiated by the current user`);
              eligibleAssets.push(asset);
              setOwnAssetsCount(prev => prev + 1);
            }
          } catch (error) {
            console.error(`Error fetching transaction for ${asset.ipId}:`, error);
          }
        }
        
        setTotalCount(eligibleAssets.length);
        console.log("Eligible assets for claiming:", eligibleAssets);
        
        // Claim royalties for eligible assets
        let totalClaimedAmount = 0;
        
        for (const asset of eligibleAssets) {
          setProcessedCount(prev => prev + 1);
          const result = await handleClaimRoyalty(asset.ipId);
          
          if (result.success && result.amount) {
            totalClaimedAmount += parseFloat(result.amount);
          }
        }
        
        // 모든 자산 처리 후 최종 클레임 결과 설정
        setClaimResult({
          claimedTokens: totalClaimedAmount.toString(),
          totalClaimed: eligibleAssets.length
        });
        
        setIsLoading(false);
      } catch (e) {
        console.error("Error in getIpaAssets:", e);
        setIsLoading(false);
        
        // 오류 발생 시 실패 상태 설정
        setClaimResult({
          success: false
        });
      }
    };
    
    if (address) {
      getIpaAssets();
    }
  }, [address]);

  async function handleClaimRoyalty(ancestorIpId: string, childIpId?: string) {
    if (!client) return { success: false };
    if (!ancestorIpId) {
      console.error("Missing IP ID");
      return { success: false };
    }
    console.log("Claiming royalty for IP ID:", ancestorIpId);

    try {
      const childIpIds = childIpId ? [childIpId] : [];
      const response = await claimAllPossibleRevenue(
        client,
        ancestorIpId,
        childIpIds
      );
      console.log("Claim response:", response);

      if (response.claimedTokens && response.claimedTokens.length > 0) {
        const claimedAmount = formatEther(response.claimedTokens[0].amount);
        console.log(`Royalties claimed:`, response.claimedTokens[0]);
        return { 
          success: true, 
          amount: claimedAmount 
        };
      } else {
        console.log("No tokens claimed");
        return { success: true, amount: "0" };
      }
    } catch (error) {
      console.error("Royalty claim failed:", error);
      return { success: false };
    }
  }

  return (
    <div className="p-4">
      <h1 className="text-xl font-bold mb-4">Claim royalty</h1>
      
      {isLoading && (
        <div className="mt-4 p-4 border rounded-lg bg-blue-50">
          <h2 className="text-lg font-semibold mb-2">Processing assets...</h2>
          <p>{ownAssetsCount} assets are found</p>
          <p>{processedCount} / {totalCount} assets checked</p>
          <div className="w-full bg-gray-200 rounded-full h-2.5 mt-2">
            <div 
              className="bg-blue-600 h-2.5 rounded-full" 
              style={{ width: `${totalCount ? (processedCount / totalCount) * 100 : 0}%` }}
            ></div>
          </div>
        </div>
      )}
      
      {claimResult.totalClaimed && !isLoading && (
        <div className="mt-4 p-4 border rounded-lg bg-green-50">
          <h2 className="text-lg font-semibold mb-2">{claimResult.claimedTokens !== "0" ? "Claim success!" : "You have nothing to claim yet"}</h2>
          <p className="font-medium">Claimed token:</p>
          <pre className="bg-gray-100 p-2 rounded mt-1 overflow-auto">
            {claimResult.claimedTokens || 0} IP
          </pre>
          <p className="mt-2 text-sm text-gray-600">
            Processed {claimResult.totalClaimed || 0} eligible assets
          </p>
        </div>
      )}

      {claimResult.success === false && !isLoading && (
        <div className="mt-4 p-4 border rounded-lg bg-red-50">
          <h2 className="text-lg font-semibold text-red-600">Claim fail</h2>
          <p>Check the console for more details.</p>
        </div>
      )}
    </div>
  );
}