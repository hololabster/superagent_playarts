"use client";

import { getDefaultConfig, TomoEVMKitProvider } from "@tomo-inc/tomo-evm-kit";
import { WagmiProvider } from "wagmi";
import { QueryClientProvider, QueryClient } from "@tanstack/react-query";
import {
  metaMaskWallet,
  rainbowWallet,
  walletConnectWallet,
} from "@tomo-inc/tomo-evm-kit/wallets";
import { storyChain, arbitrum } from "@/constants/chains";
import React, { createContext, useContext, useEffect, useState } from "react";
import { StoryClient } from "@story-protocol/core-sdk";
import { useWalletClient } from "wagmi";
import { setupStoryClient } from "@/utils/client";

const config = getDefaultConfig({
  clientId: process.env.NEXT_PUBLIC_TOMO_CLIENT_ID!,
  appName: "Ai Agent",
  projectId: process.env.NEXT_PUBLIC_WALLET_CONNECT_PROJECT_ID!,
  chains: [storyChain, arbitrum],
  ssr: true,
  wallets: [
    {
      groupName: "Popular",
      wallets: [metaMaskWallet, rainbowWallet, walletConnectWallet],
    },
  ],
});

const queryClient = new QueryClient();

// Story Client Context 정의
interface StoryClientContextType {
  client: StoryClient | null;
  isLoading: boolean;
  error: Error | null;
}

const StoryClientContext = createContext<StoryClientContextType>({
  client: null,
  isLoading: false,
  error: null,
});

export function useStoryClient() {
  return useContext(StoryClientContext);
}

// StoryClientProvider 컴포넌트
function StoryClientProvider({ children }: { children: React.ReactNode }) {
  const { data: wallet } = useWalletClient();
  const [client, setClient] = useState<StoryClient | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<Error | null>(null);

  useEffect(() => {
    async function initializeClient() {
      if (!wallet) {
        setClient(null);
        return;
      }

      setIsLoading(true);
      setError(null);

      try {
        const newClient = await setupStoryClient(wallet);
        setClient(newClient);
      } catch (err) {
        setError(
          err instanceof Error
            ? err
            : new Error("Failed to initialize Story client")
        );
      } finally {
        setIsLoading(false);
      }
    }

    initializeClient();
  }, [wallet]);

  return (
    <StoryClientContext.Provider value={{ client, isLoading, error }}>
      {children}
    </StoryClientContext.Provider>
  );
}

export function Providers({ children }: { children: React.ReactNode }) {
  return (
    <WagmiProvider config={config}>
      <QueryClientProvider client={queryClient}>
        <TomoEVMKitProvider>
          <StoryClientProvider>{children}</StoryClientProvider>
        </TomoEVMKitProvider>
      </QueryClientProvider>
    </WagmiProvider>
  );
}
