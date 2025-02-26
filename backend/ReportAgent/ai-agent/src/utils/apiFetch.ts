// utils/api.ts

import { toast } from "react-hot-toast";

interface FetchOptions extends RequestInit {
  fetch?: typeof fetch;
}

// 인증 관련 타입
interface User {
  token: string;
  // 기타 사용자 정보
}

export async function fetchWithAuth(url: string, options: FetchOptions = {}) {
  // Next.js에서는 로컬 스토리지나 쿠키에서 토큰을 가져옴
  const token = localStorage.getItem("token"); // 또는 쿠키에서 가져오기

  if (!token) {
    throw new Error("No authentication token available");
  }

  const headers: HeadersInit = {
    Accept: "*/*",
    Authorization: `Bearer ${token}`,
    ...(!options.body ||
      (!(options.body instanceof FormData) && {
        "Content-Type": "application/json",
      })),
    ...options.headers,
  };

  try {
    const response = await fetch(url, {
      ...options,
      headers,
      credentials: "include",
    });

    if (response.status === 401) {
      const result = await response.json();
      alert(result.error || "Unauthorized");
      // toast.error(result.error || "Unauthorized");
      // 로그아웃 처리
      localStorage.removeItem("token");
      window.location.href = "/login"; // 또는 Next.js router 사용
      throw new Error("Unauthorized");
    }

    if (!response.ok) {
      const clonedResponse = response.clone();
      const contentType = response.headers.get("content-type");

      if (contentType?.includes("application/json")) {
        const errorData = await response.json();
        throw new Error(errorData.message || "An error occurred");
      } else {
        const errorText = await clonedResponse.text();
        throw new Error(errorText || "An error occurred");
      }
    }

    const clonedResponse = response.clone();
    try {
      return await response.json();
    } catch {
      return await clonedResponse.text();
    }
  } catch (error) {
    console.error("API Error:", error);
    throw error;
  }
}

export async function fetchOnly(url: string, options: FetchOptions = {}) {
  const headers: HeadersInit = {
    Accept: "*/*",
    ...(!options.body ||
      (!(options.body instanceof FormData) && {
        "Content-Type": "application/json",
      })),
    ...options.headers,
  };

  try {
    const response = await fetch(url, {
      ...options,
      headers,
    });

    if (!response.ok) {
      const clonedResponse = response.clone();
      const contentType = response.headers.get("content-type");

      if (contentType?.includes("application/json")) {
        const errorData = await response.json();
        throw new Error(errorData.message || "An error occurred");
      } else {
        const errorText = await clonedResponse.text();
        throw new Error(errorText || "An error occurred");
      }
    }

    const clonedResponse = response.clone();
    try {
      return await response.json();
    } catch {
      return await clonedResponse.text();
    }
  } catch (error) {
    console.error("API Error:", error);
    throw error;
  }
}
