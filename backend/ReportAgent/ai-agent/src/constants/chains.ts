// 체인별 컨트랙트 주소 매핑
export const CONTRACT_ADDRESSES = {
  1514: "0xDE02C37eBfa259AB0D8A92C416ebc2B97FE08aA7", // Story mainnet
  1315: "0xeb662CAbca1E47ff6B41d14797f942386eBa1e28", // Story aeneid
  42161: "0xCf3380eDaCfAcc4503dAE0906F5C021e39dBfe2d", // Arbitrum
  421614: "0x5D0353812DC3d32052FbC8fE3dF838F257B9c947", // Arbitrum Sepolia
};

// // 아비트럼 테스트넷
const arbitrumSepoliaChain = {
  id: 421614,
  name: "Arbitrum Sepolia",
  nativeCurrency: {
    name: "Arbitrum Sepolia Ether",
    symbol: "ETH",
    decimals: 18,
  },
  rpcUrls: {
    default: {
      http: [
        "https://arb-sepolia.g.alchemy.com/v2/UsJlLUCWS3mrrFWSp58IpoVyP8urFINA",
      ],
    },
  },
  blockExplorers: {
    default: {
      name: "Arbiscan",
      url: "https://sepolia.arbiscan.io",
      apiUrl: "https://api-sepolia.arbiscan.io/api",
    },
  },
  contracts: {
    multicall3: {
      address: "0xca11bde05977b3631167028862be2a173976ca11",
      blockCreated: 81930,
    },
  },
  testnet: true,
};

// 아비트럼
const arbitrumChain = {
  id: 42161,
  name: "Arbitrum One",
  nativeCurrency: {
    name: "Ether",
    symbol: "ETH",
    decimals: 18,
  },
  rpcUrls: {
    default: {
      http: [
        "https://arb-mainnet.g.alchemy.com/v2/Q5mp03oKqpbsMUyLFO-HAWe0RkigVtDi",
      ],
    },
  },
  blockExplorers: {
    default: {
      name: "Arbiscan",
      url: "https://arbiscan.io",
      apiUrl: "https://api.arbiscan.io/api",
    },
  },
  contracts: {
    multicall3: {
      address: "0xca11bde05977b3631167028862be2a173976ca11",
      blockCreated: 7654707,
    },
  },
};

// Story mainnet
const storyMainnet = {
  id: 1514,
  name: "story",
  network: "mainnet",
  nativeCurrency: {
    decimals: 18,
    name: "IP",
    symbol: "IP",
  },
  rpcUrls: {
    default: {
      http: ["https://mainnet.storyrpc.io"],
    },
  },
  blockExplorers: {
    default: {
      name: "StoryScan",
      url: "https://storyscan.xyz",
    },
  },
  testnet: true,
};

// 스토리 aeneid
const storyAeneidChain = {
  id: 1315,
  name: "story",
  network: "aeneid",
  nativeCurrency: {
    decimals: 18,
    name: "IP",
    symbol: "IP",
  },
  rpcUrls: {
    default: {
      http: ["https://aeneid.storyrpc.io"],
    },
  },
  blockExplorers: {
    default: {
      name: "StoryScan",
      url: "https://aeneid.storyscan.xyz/",
    },
  },
  testnet: true,
};

export const arbitrum =
  process.env.NODE_ENV === "production" ? arbitrumChain : arbitrumSepoliaChain;

export const storyChain =
  process.env.NODE_ENV === "production" ? storyMainnet : storyAeneidChain;

export const storyContractAddress =
  process.env.NODE_ENV === "production"
    ? CONTRACT_ADDRESSES[1514]
    : CONTRACT_ADDRESSES[1315];
