import { createContext, useContext, useMemo, useState } from "react";
import { configureApiAuth } from "../services/api";

const AuthContext = createContext(null);

function decodeJwt(token) {
  try {
    const [, payloadPart] = token.split(".");
    const payload = JSON.parse(atob(payloadPart));
    return {
      email: payload.email || payload.sub || "",
      role: payload.role || "customer",
    };
  } catch {
    return { email: "", role: "customer" };
  }
}

let currentToken = null;
configureApiAuth({
  getToken: () => currentToken,
  onUnauthorized: () => {},
});

export function AuthProvider({ children }) {
  const [token, setToken] = useState(null);
  const [user, setUser] = useState(null);
  const [sessionExpiredMessage, setSessionExpiredMessage] = useState("");

  const login = (newToken) => {
    currentToken = newToken;
    setToken(newToken);
    setUser(decodeJwt(newToken));
    setSessionExpiredMessage("");
  };

  const logout = (message = "") => {
    currentToken = null;
    setToken(null);
    setUser(null);
    setSessionExpiredMessage(message);
  };

  const value = useMemo(
    () => ({ token, user, login, logout, sessionExpiredMessage }),
    [token, user, sessionExpiredMessage]
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used within AuthProvider");
  }
  return context;
}