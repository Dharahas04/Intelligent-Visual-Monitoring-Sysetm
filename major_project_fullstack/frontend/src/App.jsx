import { useState } from "react";
import { loginUser, registerUser } from "./api";
import AuthScreen from "./components/AuthScreen";
import Dashboard from "./components/Dashboard";

const STORAGE_KEY = "major_project_auth_v1";

function getInitialAuthState() {
  const raw = localStorage.getItem(STORAGE_KEY);
  if (!raw) {
    return null;
  }
  try {
    return JSON.parse(raw);
  } catch (error) {
    localStorage.removeItem(STORAGE_KEY);
    return null;
  }
}

function App() {
  const [auth, setAuth] = useState(getInitialAuthState);
  const [mode, setMode] = useState("login");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const handleAuthSubmit = async ({ fullName, email, password }) => {
    setLoading(true);
    setError("");
    try {
      const payload =
        mode === "register"
          ? await registerUser({ fullName, email, password })
          : await loginUser({ email, password });

      const nextAuth = {
        token: payload.token,
        fullName: payload.fullName,
        email: payload.email
      };
      localStorage.setItem(STORAGE_KEY, JSON.stringify(nextAuth));
      setAuth(nextAuth);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleLogout = () => {
    localStorage.removeItem(STORAGE_KEY);
    setAuth(null);
    setMode("login");
  };

  if (!auth?.token) {
    return (
      <AuthScreen
        mode={mode}
        setMode={setMode}
        onSubmit={handleAuthSubmit}
        loading={loading}
        error={error}
      />
    );
  }

  return (
    <Dashboard
      token={auth.token}
      profile={{ fullName: auth.fullName, email: auth.email }}
      onLogout={handleLogout}
    />
  );
}

export default App;
