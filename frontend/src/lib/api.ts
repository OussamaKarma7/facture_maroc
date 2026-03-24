import { getToken, removeToken } from "./auth";

const envUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
export const API_BASE_URL = envUrl.endsWith("/api") ? envUrl : `${envUrl}/api`;

interface FetchOptions extends Omit<RequestInit, 'body'> {
  requireAuth?: boolean;
  body?: any;
}

export async function apiFetch(endpoint: string, options: FetchOptions = {}) {
  const { requireAuth = true, ...customOptions } = options;
  const headers = new Headers(customOptions.headers);

  // Default to JSON if not explicitly set and body is present (except FormData/URLSearchParams)
  if (customOptions.body && !(customOptions.body instanceof FormData) && !(customOptions.body instanceof URLSearchParams)) {
      if (!headers.has("Content-Type")) {
          headers.set("Content-Type", "application/json");
      }
      if (typeof customOptions.body === "object") {
          customOptions.body = JSON.stringify(customOptions.body);
      }
  }

  if (requireAuth) {
    const token = getToken();
    if (token) {
      headers.set("Authorization", `Bearer ${token}`);
    } else {
        // Handle redirect to login if explicitly required and no token
        if (typeof window !== "undefined") {
            window.location.href = "/login";
        }
    }
  }

  const url = `${API_BASE_URL}${endpoint}`;

  try {
    const response = await fetch(url, {
      ...customOptions,
      headers,
    });

    if (response.status === 401) {
      // Unauthorized: clear token and redirect
      removeToken();
      if (typeof window !== "undefined" && window.location.pathname !== "/login") {
        window.location.href = "/login";
      }
      throw new Error("Unauthorized");
    }

    if (!response.ok) {
      const errorData = await response.json().catch(() => null);
      throw new Error(errorData?.detail || `Error: ${response.status}`);
    }

    // Return null if no content (e.g., DELETE)
    if (response.status === 204) {
      return null;
    }
    
    // Check if response is raw binary (PDF)
    const contentType = response.headers.get("content-type");
    if (contentType && contentType.includes("application/pdf")) {
      return response.blob();
    }

    return response.json();
  } catch (error) {
    console.error("API Error:", error);
    throw error;
  }
}
