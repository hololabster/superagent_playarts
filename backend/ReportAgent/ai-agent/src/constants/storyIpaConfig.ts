import { LicenseTerms } from "@story-protocol/core-sdk";
import { zeroAddress } from "viem";

export const aeneidRoyaltyPolicy = "0xBe54FB168b3c982b7AaE60dB6CF75Bd8447b390E";
export const commercialRevShare = 10; // 원작자에게 수익의 10% 분배

export const defaultLicenseTermData: LicenseTerms = {
  defaultMintingFee: 10_000_000n,
  currency: "0x1514000000000000000000000000000000000000",
  royaltyPolicy: aeneidRoyaltyPolicy,
  transferable: true,
  expiration: 0n,
  commercialUse: true,
  commercialAttribution: true,
  commercializerChecker: zeroAddress,
  commercializerCheckerData: "0x",
  commercialRevShare: commercialRevShare, // 원작자의 수익 %
  commercialRevCeiling: 0n,
  derivativesAllowed: true,
  derivativesAttribution: true,
  derivativesApproval: false,
  derivativesReciprocal: true,
  derivativeRevCeiling: 0n,
  uri: "",
};
