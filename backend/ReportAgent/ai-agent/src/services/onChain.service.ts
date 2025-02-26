import { storyContractAddress, storyChain } from "@/constants/chains";
import { contractABI } from "@/constants/contractABI";
import { MAKE_NFT_FEE } from "@/constants/price";
import {
  createPublicClient,
  http,
  createWalletClient,
  parseUnits,
  formatUnits,
  custom,
  decodeEventLog,
} from "viem";

// Price Feed ABI
const priceFeedABI = [
  {
    inputs: [],
    name: "latestRoundData",
    outputs: [
      { name: "roundId", type: "uint80" },
      { name: "answer", type: "int256" },
      { name: "startedAt", type: "uint256" },
      { name: "updatedAt", type: "uint256" },
      { name: "answeredInRound", type: "uint80" },
    ],
    stateMutability: "view",
    type: "function",
  },
  {
    inputs: [],
    name: "decimals",
    outputs: [{ name: "", type: "uint8" }],
    stateMutability: "view",
    type: "function",
  },
];

/**
 * NFT 민팅 온체인 프로세스 실행 함수
 */
export async function mintNFTOnChain(
  metadataURI: string
): Promise<{ txHash: `0x${string}`; receipt: any }> {
  try {
    // 지갑 연결 확인
    if (!window.ethereum) {
      throw new Error(
        "No ethereum provider found. Please install MetaMask or another wallet."
      );
    }

    // viem 클라이언트 생성
    const publicClient = createPublicClient({
      chain: storyChain,
      transport: http(),
    });

    const walletClient = createWalletClient({
      chain: storyChain,
      transport: custom(window.ethereum),
    });

    // 계정 가져오기
    const [address] = await walletClient.getAddresses();
    if (!address) {
      throw new Error("No wallet account found");
    }

    // 컨트랙트에서 Token/USD 가격 가져오기
    const tokenUsdPriceWei = (await publicClient.readContract({
      address: storyContractAddress,
      abi: contractABI,
      functionName: "getTokenPriceInUSD",
    })) as bigint;

    console.log("Contract Token/USD Price (Wei):", tokenUsdPriceWei.toString());

    // 필요한 Token 금액 계산 (BigInt 사용)
    const MAKE_NFT_FEE_WEI = parseUnits(MAKE_NFT_FEE.toString(), 18); // $1.99를 Wei로 변환
    console.log("MAKE_NFT_FEE (Wei):", MAKE_NFT_FEE_WEI.toString());

    // 정확한 계산을 위해 BigInt 산술 사용
    // requiredTokenAmount = (MAKE_NFT_FEE_WEI * 10^18) / tokenUsdPriceWei
    const ONE_ETHER = BigInt(10) ** BigInt(18);
    const requiredTokenAmountWei =
      (MAKE_NFT_FEE_WEI * ONE_ETHER) / tokenUsdPriceWei;

    console.log(
      "Required Token Amount (Wei):",
      requiredTokenAmountWei.toString()
    );

    // NFT 민팅 트랜잭션 시뮬레이션
    const { request } = await publicClient.simulateContract({
      address: storyContractAddress,
      abi: contractABI,
      functionName: "create721Nft",
      args: [metadataURI],
      account: address,
      value: requiredTokenAmountWei,
    });

    // 트랜잭션 전송
    const txHash = await walletClient.writeContract(request);
    console.log("NFT transaction sent:", txHash);

    // 트랜잭션 완료 대기
    const receipt = await publicClient.waitForTransactionReceipt({
      hash: txHash,
    });

    // Transfer 이벤트에서 tokenId 확인
    const transferEvents = receipt.logs
      .filter(
        (log) =>
          log.address.toLowerCase() === storyContractAddress.toLowerCase()
      )
      .map((log) => {
        try {
          // ERC-721 Transfer 이벤트 디코딩 시도
          return decodeEventLog({
            abi: contractABI,
            data: log.data,
            topics: log.topics,
          });
        } catch (e) {
          return null;
        }
      })
      .filter((event) => event?.eventName === "Transfer");

    if (transferEvents.length > 0) {
      // 마지막 Transfer 이벤트에서 tokenId 가져오기
      const tokenId = transferEvents[transferEvents.length - 1].args.tokenId;
      console.log("Minted NFT Token ID:", tokenId.toString());
      return { txHash, receipt, tokenId };
    } else {
      console.warn("No Transfer event found in transaction receipt");
      return { txHash, receipt };
    }
  } catch (error) {
    console.error("Minting error:", error);
    throw error;
  }
}
