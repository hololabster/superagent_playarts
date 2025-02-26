"use client";
import { useAccountModal, useConnectModal } from "@tomo-inc/tomo-evm-kit";
import styles from "./Header.module.scss";
import { useAccount, useBalance } from "wagmi";
import { Button } from "@/components/common/Button/Button";
import WalletIcon from "@/assets/icons/wallet.svg";
import { getNonce } from "@/services/auth.service";

export function WallectConnect() {
  const { openAccountModal } = useAccountModal();
  const { openConnectModal } = useConnectModal();
  const { address, isConnected } = useAccount();

  const { data: balance, isLoading } = useBalance({ address: address });

  console.log(address, isConnected, balance, isLoading);

  const formatBalance = (balance: number | undefined) => {
    if (!balance) return "0";
    return Number(balance).toLocaleString(undefined, {
      minimumFractionDigits: 2,
      maximumFractionDigits: 4,
    });
  };

  const handleSignMessage = async () => {
    if (address) {
      console.log(address);
      const nonce = await getNonce(address);

      console.log(nonce);
      const message = nonce;
    }
  };

  return (
    <>
      {!isConnected ? (
        <Button type="D" content="LOGIN" onClick={openConnectModal} />
      ) : (
        <div className={styles.wallet_info} onClick={openAccountModal}>
          <WalletIcon />
          <p>
            {formatBalance(Number(balance?.formatted))} {balance?.symbol}
          </p>
        </div>
      )}

      {/* <button onClick={handleSignMessage}>nonce</button> */}
    </>
  );
}
