import { FormEvent, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "../auth";

export function LoginPage() {
  const { login } = useAuth();
  const navigate = useNavigate();
  const [username, setUsername] = useState("admin");
  const [password, setPassword] = useState("admin12345");
  const [error, setError] = useState<string | null>(null);

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    setError(null);
    try {
      await login(username, password);
      navigate("/dashboard");
    } catch {
      setError("Login failed");
    }
  }

  return (
    <div className="login-wrap">
      <div className="card login-card">
        <h2>Platform Login</h2>
        <form onSubmit={onSubmit} className="row">
          <input value={username} onChange={(e) => setUsername(e.target.value)} placeholder="Username" />
          <input
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            placeholder="Password"
          />
          <button type="submit">Sign In</button>
          {error && <p style={{ color: "#b91c1c" }}>{error}</p>}
        </form>
      </div>
    </div>
  );
}
