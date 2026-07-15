import { useState } from "react";
import { useNavigate, Link } from "react-router-dom";

import { useAuth } from "../context/AuthContext";
import { loginRequest } from "../services/api";

export default function LoginPage() {
  const navigate = useNavigate();
  const { login, sessionExpiredMessage } = useAuth();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function handleSubmit(event) {
    event.preventDefault();
    setError("");
    setLoading(true);

    try {
      const data = await loginRequest(email, password);
      login(data.access_token);
      navigate("/chat", { replace: true });
    } catch (requestError) {
      setError(requestError.message || "Login failed");
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="login-page">
      <form className="auth-card" onSubmit={handleSubmit}>
        <h1>Datamart Chatbot</h1>
        <p>Sign in to continue.</p>

        {sessionExpiredMessage ? <p className="session-expired">{sessionExpiredMessage}</p> : null}
        {error ? <p className="error-message">{error}</p> : null}

        <label htmlFor="email">Email</label>
        <input
          id="email"
          type="email"
          value={email}
          onChange={(event) => setEmail(event.target.value)}
          required
        />

        <label htmlFor="password">Password</label>
        <input
          id="password"
          type="password"
          value={password}
          onChange={(event) => setPassword(event.target.value)}
          required
        />

        <button type="submit" className="button" disabled={loading}>
          {loading ? "Signing in..." : "Login"}
        </button>

        <p style={{ marginTop: "12px", fontSize: "13px" }}>
          Don't have an account? <Link to="/signup">Sign up</Link>
        </p>
      </form>
    </main>
  );
}