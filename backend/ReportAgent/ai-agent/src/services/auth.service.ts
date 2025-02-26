import { fetchOnly, fetchWithAuth } from "@/utils/apiFetch";

const AUTH_URL = process.env.NEXT_PUBLIC_AUTH_URL;

// getNonce 잘됨
export async function getNonce(address: string) {
  try {
    const response = await fetchOnly(
      `${AUTH_URL}/Wallet/nonce?address=${address}`
    );

    const data = response;
    return data.nonce;
  } catch (error) {
    console.error("Error getting nonce:", error);
    throw error;
  }
}

interface WallectLogin {
  address: string;
  signedmessage: string;
  originalmessage: string | null;
  refCode: string | null;
}

export async function walletLogin({
  address,
  signedmessage,
  originalmessage,
  refCode = null,
}: WallectLogin) {
  try {
    const response = await fetchOnly(`${AUTH_URL}/Wallet/wallet-login`, {
      method: "POST",
      body: JSON.stringify({
        Address: address,
        SignedMessage: signedmessage,
        OriginalMessage: originalmessage,
        ReferralCode: refCode, // 레퍼럴 코드 추가
      }),
    });

    const data = response;

    return data;
  } catch (error) {
    console.error("Error during wallet login:", error);
    return { success: false, error: error.message };
  }
}

export async function checkEmailVerification(email: string) {
  try {
    const response = await fetchWithAuth(
      `${AUTH_URL}/Auth/check-email-verification?email=${email}`
    );
    return { success: true, data: response };
  } catch (error) {
    console.error("Error getting check email verification:", error);
    return { success: false, error: error.message };
  }
}
