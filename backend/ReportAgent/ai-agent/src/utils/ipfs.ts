import { PinataSDK } from "pinata-web3";
import { createHash } from "crypto";

const pinata = new PinataSDK({
  pinataJwt: `${process.env.NEXT_PUBLIC_PINATA_JWT}`,
  pinataGateway: `${process.env.NEXT_PUBLIC_GATEWAY_URL}`,
});

export async function uploadJSONToIPFS(jsonMetadata: any): Promise<string> {
  const { IpfsHash } = await pinata.upload.json(jsonMetadata);
  return IpfsHash;
}

export function createMetadataHash(metadata: any): string {
  return createHash("sha256").update(JSON.stringify(metadata)).digest("hex");
}
