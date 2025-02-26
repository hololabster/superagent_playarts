"use client";

import styles from "./Header.module.scss";
import { WallectConnect } from "./WalletConnect";
import { useAside } from "@/context/AsideContext";
import AsideBtn from "@/assets/icons/aside_open_close.svg";

export function Headeer() {
  const { isAsideOpen, setIsAsideOpen } = useAside();

  return (
    <header className={styles.header}>
      <div className={styles.inner_header}>
        <div className={styles.left}>
          {!isAsideOpen && (
            <button
              className={styles.open_btn}
              onClick={() => setIsAsideOpen(true)}
            >
              <AsideBtn />
            </button>
          )}

          <button className={styles.main_logo}>
            <img src="/images/playarts_logo.png" alt="playarts_logo" />
          </button>
        </div>

        <div className={styles.right}>
          <WallectConnect />
        </div>
      </div>
    </header>
  );
}
