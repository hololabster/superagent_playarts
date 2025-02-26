import { custom } from "viem";
import { StoryClient, StoryConfig } from "@story-protocol/core-sdk";
import { UseWalletClientReturnType } from "wagmi";

export async function setupStoryClient(
  wallet: NonNullable<UseWalletClientReturnType["data"]>
): Promise<StoryClient> {
  const config: StoryConfig = {
    account: wallet.account,
    transport: custom(wallet.transport),
    chainId: "aeneid",
  };
  return StoryClient.newClient(config);
}
