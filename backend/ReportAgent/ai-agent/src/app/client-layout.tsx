// src/app/client-layout.tsx
"use client";
import { Headeer } from "@/components/layout/Header/Header";
import { Aside } from "@/components/layout/Aside/Aside";
import styles from "./layout.module.scss";
import { AsideProvider, useAside } from "@/context/AsideContext";

interface ClientLayoutProps {
  children: React.ReactNode;
}

function MainContent({ children }: { children: React.ReactNode }) {
  const { isAsideOpen } = useAside();

  return (
    <main
      className={`${styles.main} ${
        isAsideOpen ? styles.with_aside : styles.without_aside
      }`}
    >
      <Headeer />
      {children}
    </main>
  );
}

export function ClientLayout({ children }: ClientLayoutProps) {
  return (
    <AsideProvider>
      {/* <Headeer /> */}
      <div className={styles.container}>
        <Aside />
        <MainContent>{children}</MainContent>
      </div>
    </AsideProvider>
  );
}
