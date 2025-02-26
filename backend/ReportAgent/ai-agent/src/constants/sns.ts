import XIcon from "@/assets/icons/x.svg";
import LinkedinIcon from "@/assets/icons/linkedin.svg";
import MediumIcon from "@/assets/icons/medium.svg";
import { FunctionComponent, SVGProps } from "react";

interface SnsType {
  name: string;
  link: string;
  icon: FunctionComponent<SVGProps<SVGAElement>>;
}

export const snsLinks: SnsType[] = [
  {
    name: "x",
    link: "https://x.com/playartsdotai",
    icon: XIcon,
  },
  {
    name: "linkedin",
    link: "https://www.linkedin.com/company/playartsai",
    icon: LinkedinIcon,
  },
  {
    name: "medium",
    link: "https://medium.com/@PlayArtsAI",
    icon: MediumIcon,
  },
];
