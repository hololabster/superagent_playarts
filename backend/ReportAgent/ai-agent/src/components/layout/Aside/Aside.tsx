"use client";
import styles from "./Aside.module.scss";
import { useAside } from "@/context/AsideContext";
import AsideIcon from "@/assets/icons/aside_open_close.svg";
import Link from "next/link";
import Image from "next/image";
import { usePathname } from "next/navigation";
import { snsLinks } from "@/constants/sns";

export function Aside() {
  const pathname = usePathname();
  const { isAsideOpen, setIsAsideOpen } = useAside();
  return (
    <aside
      className={`${styles.aside} ${isAsideOpen ? styles.open : styles.closed}`}
    >
      <div className={styles.top}>
        <button className={styles.main_logo}>
          <Image src="/images/playarts_logo.png" alt="playarts_logo" fill />
        </button>
        <button
          className={styles.close_btn}
          onClick={() => setIsAsideOpen(false)}
        >
          <AsideIcon />
        </button>
      </div>

      <div className={styles.container}>
        <nav className={styles.nav}>
          <ul>
            <li>
              <Link href="/" className={pathname === "/" ? styles.active : ""}>
                Home
              </Link>
            </li>
            {/* <li>
              <Link
                href="/point"
                className={pathname === "/point" ? styles.active : ""}
              >
                Point
              </Link>
            </li> */}
          </ul>
        </nav>

        <div className={styles.sns_wrap}>
          <ul>
            {snsLinks.map(({ name, link, icon: Icon }) => (
              <li key={name}>
                <a href={link} target="_blank">
                  <Icon />
                </a>
              </li>
            ))}
          </ul>
        </div>
      </div>
    </aside>
  );
}
