import { Dispatch, SetStateAction, useEffect, useState } from "react";
import styles from "./Chat.module.scss";
import { useWalletClient } from "wagmi";
import { useStoryClient } from "@/app/providers";
import { mintLicenseToken } from "@/services/ipa.service";
import { Button } from "../common/Button/Button";
import { typeMessage } from "@/utils/message";

interface BuyLicenseTokenProp {
  ipId: string;
  licenseTermsId: string;
  setMessages: Dispatch<SetStateAction<MessageWithLoading[]>>;
  setIsAITyping: Dispatch<SetStateAction<boolean>>;
}
export default function BuyLicenseToken({
  ipId,
  licenseTermsId,
  setMessages,
  setIsAITyping,
}: BuyLicenseTokenProp) {
  const { data: wallet } = useWalletClient();
  const { client } = useStoryClient();
  const [amount, setAmount] = useState(1);
  const [buttonStatus, setButtonStatus] = useState(""); //"", loading, done
  useEffect(() => {
    console.log("BuyLicenseToken props:", { ipId, licenseTermsId });
  }, [ipId, licenseTermsId]);

  async function handleMintLicense() {
    if (!wallet || !client) return;
    if (licenseTermsId && ipId) {
      try {
        setButtonStatus("loading");
        const response = await mintLicenseToken(client, {
          licenseTermsId: licenseTermsId,
          licensorIpId: ipId,
          amount: amount,
          // parentIpId,
        });

        console.log(`Successfully minted license tokens`);
        console.log(`Tx hash: ${response.txHash}`);
        console.log(`License token IDs: ${response.licenseTokenIds}`);
        setButtonStatus("done");
        typeMessage(
          "Successfully minted license tokens!",
          setMessages,
          setIsAITyping
        );
      } catch (error) {
        console.error("Failed to mint license tokens:", error);
        alert("Failed to mint license tokens. Check console for details.");
        setButtonStatus("");
      }
    } else {
      return;
    }
  }

  return (
    <div className={styles.license_token_container}>
      <h4>You need to mint license token to use this IPA filter</h4>
      <div className={styles.buy_token_area}>
        <label htmlFor="tokenAmount">1 License Token per 1 month</label>
        <input
          name="tokenAmount"
          type="number"
          min="1"
          className="border-black box-border border-solid border p-2"
          placeholder="Token Amount"
          value={amount}
          onChange={(e) => setAmount(parseInt(e.target.value))}
        />
        <Button
          type="A"
          content={buttonStatus == "done" ? "Done!" : "Mint License token"}
          onClick={handleMintLicense}
          loading={buttonStatus == "loading"}
          disabled={buttonStatus == "loading" || buttonStatus == "done"}
        />
      </div>
    </div>
  );
}
