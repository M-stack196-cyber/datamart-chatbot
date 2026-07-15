import { Navigate, Route, Routes } from "react-router-dom";
import { useEffect } from "react";

import { useAuth } from "./context/AuthContext";
import { configureApiAuth } from "./services/api";
import ChatPage from "./pages/ChatPage";
import LoginPage from "./pages/LoginPage";
import SignupPage from "./pages/SignupPage";
import AdminPage from "./pages/AdminPage";

function ProtectedRoute({ children, adminOnly = false }) {
  const { token, user } = useAuth();

  if (!token) {
    return <Navigate to="/login" replace />;
  }

  if (adminOnly && user?.role !== "admin") {
    return <Navigate to="/chat" replace />;
  }

  return children;
}

export default function App() {
  const { token, logout } = useAuth();
useEffect(() => {
  configureApiAuth({
    onUnauthorized: () => logout("Your session expired. Please log in again."),
  });
}, [logout]);
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route path="/signup" element={<SignupPage />} />
      <Route
        path="/chat"
        element={
          <ProtectedRoute>
            <ChatPage />
          </ProtectedRoute>
        }
      />
      <Route
        path="/admin"
        element={
          <ProtectedRoute adminOnly>
            <AdminPage />
          </ProtectedRoute>
        }
      />
      <Route path="*" element={<Navigate to={token ? "/chat" : "/login"} replace />} />
    </Routes>
  );
}