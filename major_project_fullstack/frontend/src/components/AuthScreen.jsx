import { useState } from "react";

function AuthScreen({ mode, setMode, onSubmit, loading, error }) {
  const [fullName, setFullName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");

  const handleSubmit = async (event) => {
    event.preventDefault();
    await onSubmit({
      fullName,
      email,
      password
    });
  };

  return (
    <div className="auth-shell">
      <div className="noise" />
      <div className="auth-card">
        <p className="chip">IntelMon</p>
        <h1>Intelligent Visual Monitoring System</h1>
        <p className="subtext">
          IntelMon unifies ANPR, anomaly detection, crowd gathering alerts and mask compliance in one platform.
        </p>
        <form onSubmit={handleSubmit} className="auth-form">
          {mode === "register" ? (
            <label>
              Full Name
              <input
                value={fullName}
                onChange={(event) => setFullName(event.target.value)}
                required
                placeholder="Your name"
              />
            </label>
          ) : null}
          <label>
            Email
            <input
              type="email"
              value={email}
              onChange={(event) => setEmail(event.target.value)}
              required
              placeholder="name@example.com"
            />
          </label>
          <label>
            Password
            <input
              type="password"
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              required
              minLength={6}
              placeholder="At least 6 characters"
            />
          </label>
          <button type="submit" disabled={loading}>
            {loading ? "Please wait..." : mode === "register" ? "Create Account" : "Login"}
          </button>
        </form>
        {error ? <p className="error-text">{error}</p> : null}
        <p className="switcher">
          {mode === "register" ? "Already have an account?" : "New to platform?"}{" "}
          <button
            type="button"
            className="link-btn"
            onClick={() => setMode(mode === "register" ? "login" : "register")}
          >
            {mode === "register" ? "Login" : "Register"}
          </button>
        </p>
      </div>
    </div>
  );
}

export default AuthScreen;
