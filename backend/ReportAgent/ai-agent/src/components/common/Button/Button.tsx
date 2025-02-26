import { ButtonHTMLAttributes, ReactNode } from "react";
import styles from "./Button.module.scss";
// import SpinnerIcon from "@/assets/icons/spin.svg";

interface ButtonProps
  extends Omit<ButtonHTMLAttributes<HTMLButtonElement>, "type"> {
  type?: "A" | "B" | "C" | "D" | "E";
  content?: string;
  loading?: boolean;
  className?: string;
  style?: React.CSSProperties;
  children?: ReactNode;
}

export function Button({
  type = "A",
  content,
  loading = false,
  className = "",
  style,
  children,
  ...props
}: ButtonProps) {
  return (
    <button
      className={`${styles.button} ${styles[`btn-${type}`]} ${className}`}
      style={style}
      {...props}
    >
      {content}
      {children}
      {loading && (
        <svg
          xmlns="http://www.w3.org/2000/svg"
          width="24"
          height="24"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="2"
          strokeLinecap="round"
          strokeLinejoin="round"
          className={styles.animateSpin}
        >
          <path d="M12 2v4" />
          <path d="m16.2 7.8 2.9-2.9" />
          <path d="M18 12h4" />
          <path d="m16.2 16.2 2.9 2.9" />
          <path d="M12 18v4" />
          <path d="m4.9 19.1 2.9-2.9" />
          <path d="M2 12h4" />
          <path d="m4.9 4.9 2.9 2.9" />
        </svg>
      )}
      {/* {loading && <SpinnerIcon className={styles.animateSpin} />} */}
    </button>
  );
}

/**
    import { Button } from '@/components/common/Button';

    // 기본 사용
    <Button content="Click me" />

    // 타입 지정
    <Button type="C" content="Rounded Button" />

    // 로딩 상태
    <Button loading content="Loading..." />

    // disabled 상태
    <Button disabled content="Disabled" />

    // children 사용
    <Button type="B">
    Custom Content
    </Button>

    // 클래스 추가
    <Button className="rainbow" content="Rainbow Button" />

    // 이벤트 핸들러
    <Button 
    content="Click Handler" 
    onClick={() => console.log('clicked')}
    />

    // 인라인 스타일
    <Button 
    content="Styled Button" 
    style={{ width: '200px' }}
    />
 */
