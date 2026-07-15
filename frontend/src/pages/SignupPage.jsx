import { useState } from "react";
import { useNavigate, Link } from "react-router-dom";

import { signupRequest } from "../services/api";

export default function SignupPage() {
  const navigate = useNavigate();
  const [fullName, setFullName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [role, setRole] = useState("customer");
  const [department, setDepartment] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [success, setSuccess] = useState("");

  async function handleSubmit(event) {
    event.preventDefault();
    setError("");
    setSuccess("");
    setLoading(true);

    try {
      await signupRequest({
        full_name: fullName,
        email,
        password,
        role,
        department: department || null,
      });

      if (role === "employee") {
        setSuccess("Account created. An admin needs to approve it before you can log in.");
      } else {
        setSuccess("Account created. You can log in now.");
      }
    } catch (requestError) {
      setError(requestError.message || "Signup failed");
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="login-page">
      <form className="auth-card" onSubmit={handleSubmit}>
        <h1>Datamart Chatbot</h1>
        <p>Create your account.</p>

        {error ? <p className="error-message">{error}</p> : null}
        {success ? <p className="session-expired">{success}</p> : null}

        <label htmlFor="fullName">Full name</label>
        <input
          id="fullName"
          type="text"
          value={fullName}
          onChange={(event) => setFullName(event.target.value)}
          required
        />

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

        <label htmlFor="role">I am a</label>
        <select id="role" value={role} onChange={(event) => setRole(event.target.value)}>
          <option value="customer">Customer</option>
          <option value="employee">Employee</option>
        </select>

        {role === "employee" ? (
          <>
            <label htmlFor="department">Department</label>
            <input
              id="department"
              type="text"
              value={department}
              onChange={(event) => setDepartment(event.target.value)}
              placeholder="e.g. Finance, HR"
            />
          </>
        ) : null}

        <button type="submit" className="button" disabled={loading}>
          {loading ? "Creating account..." : "Sign up"}
        </button>

        <p style={{ marginTop: "12px", fontSize: "13px" }}>
          Already have an account? <Link to="/login">Log in</Link>
        </p>
      </form>
    </main>
  );
}