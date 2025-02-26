"use client";

import {
  createContext,
  ReactNode,
  useContext,
  useEffect,
  useState,
} from "react";

interface AsideContextType {
  isAsideOpen: boolean;
  setIsAsideOpen: (open: boolean) => void;
}

const AsideContext = createContext<AsideContextType | undefined>(undefined);

export function AsideProvider({ children }: { children: ReactNode }) {
  const [isAsideOpen, setIsAsideOpen] = useState<boolean | undefined>(
    undefined
  );

  useEffect(() => {
    const updateInitialState = () => {
      setIsAsideOpen(window.innerWidth > 1440);
    };

    updateInitialState();
    let prevWidth = window.innerWidth;

    const checkScreenSize = () => {
      const currentWidth = window.innerWidth;
      const isPrevPC = prevWidth > 1440;
      const isCurrentPC = currentWidth > 1440;

      if (isPrevPC && !isCurrentPC) {
        setIsAsideOpen(false);
      }

      prevWidth = currentWidth;
    };

    window.addEventListener("resize", checkScreenSize);
    return () => window.removeEventListener("resize", checkScreenSize);
  }, []);

  if (isAsideOpen === undefined) {
    return null;
  }

  return (
    <AsideContext.Provider value={{ isAsideOpen, setIsAsideOpen }}>
      {children}
    </AsideContext.Provider>
  );
}

export function useAside() {
  const context = useContext(AsideContext);
  if (context === undefined) {
    throw new Error("useAside must be used within an AsideProvider");
  }
  return context;
}
