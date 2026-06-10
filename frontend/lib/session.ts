export const getSessionId = (): string => {
  if (typeof window === "undefined") {
    return "default";
  }

  const key = "billguard_session_id";

  let sessionId = localStorage.getItem(key);

  if (!sessionId) {
    sessionId =
      "session_" +
      Math.random().toString(36).substr(2, 9) +
      "_" +
      Date.now().toString(36);
    localStorage.setItem(key, sessionId);
  }

  return sessionId;
};

export const clearSession = (): void => {
  if (typeof window === "undefined") return;
  localStorage.removeItem("billguard_session_id");
};
