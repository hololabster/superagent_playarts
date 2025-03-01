export interface AiAgentOptionType {
  type:
    | "training"
    | "trainingNFT"
    | "analyzingNFT"
    | "analyzingWallet"
    | "generate"
    | "claim"
    | "twit"
    | "outfit";
  title: string;
}

/**
 * 1. training : 다른 API 사용 (training_character)
 *    1. 이미지 트레이닝 : 캐릭터이름, 이미지 -> Start Training
 *    2. 트레이닝 중
 *    3. 트레이닝 완료
 * 2. nft training
 *    1. NFT 검색 : 지갑주소 -> search NFTs -> nftGallery(자신의 nft 이미지)
 *    2. NFT 학습 폼 제출 : 캐릭터 이름, 선택한 NFT 이미지
 *    3. 로컬 이미지 업로드
 * 3. 온체인 nft 매매 데이터 분석 (on_chain_nft)
 * 4. 지갑분석 : (wallet_address)
 *    클릭시
 *    1. 지갑주소를 입력해주세요.
 *    2. 현재 지갑주소 텍스트란에 입력되어 있어야 된다.
 * 5. 이미지 생성 -> 클릭시 필터 선택 (예: please Generate image of "sparky" is nice guy) (generate_image)
 *    1. 입력창에 "please Generate image of" 앞에 자동으로 입력
 *    2. 필터창 나타나도록
 */

export const aiAgentOptions: AiAgentOptionType[] = [
  {
    type: "training",
    title: "Training character images",
  },
  {
    type: "trainingNFT",
    title: "Training character images NFT",
  },
  {
    type: "analyzingNFT",
    title: "Analyzing NFT markets",
  },
  {
    type: "analyzingWallet",
    title: "Analyzing wallet activity",
  },
  {
    type: "generate",
    title: "Generating images with filter name",
  },
  {
    type: "claim",
    title: "Do I have any royalties to claim?",
  },
  {
    type: "twit",
    title: "Twitter to takoyan_ai",
  },
  {
    type: "outfit",
    title: "Edit character's outfit",
  },
];
