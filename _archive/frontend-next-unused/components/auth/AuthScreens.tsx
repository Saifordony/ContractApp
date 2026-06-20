"use client";

import { useMemo, useState } from "react";
import type { FormEvent, ReactNode } from "react";
import { ApiError, login, registerUser } from "@/lib/api";

type FieldName = "name" | "email" | "password";
type TouchedState = Partial<Record<FieldName, boolean>>;
type AuthMode = "login" | "signup";

const PASSWORD_RULES = [
  { id: "length", label: "At least 8 characters", test: (value: string) => value.length >= 8 },
  { id: "letter", label: "At least one letter", test: (value: string) => /[A-Za-z]/.test(value) },
  { id: "number", label: "At least one number", test: (value: string) => /\d/.test(value) },
];

function isValidEmail(value: string): boolean {
  return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(value.trim());
}

function Spinner() {
  return <span className="auth-spinner" aria-label="Loading" />;
}

function EyeIcon({ hidden }: { hidden: boolean }) {
  return (
    <svg aria-hidden="true" viewBox="0 0 24 24" focusable="false">
      {hidden ? (
        <>
          <path d="M3 3l18 18" />
          <path d="M10.6 10.6A2 2 0 0012 14a2 2 0 001.4-.6" />
          <path d="M8.3 5.4A10.8 10.8 0 0112 4c5 0 8.5 4.3 9.7 6a12.5 12.5 0 01-3.1 3.6" />
          <path d="M6.2 7.2A13.4 13.4 0 002.3 12C3.5 13.7 7 18 12 18c1.4 0 2.7-.3 3.8-.9" />
        </>
      ) : (
        <>
          <path d="M2.3 12S5.8 6 12 6s9.7 6 9.7 6-3.5 6-9.7 6-9.7-6-9.7-6z" />
          <circle cx="12" cy="12" r="2.7" />
        </>
      )}
    </svg>
  );
}

function AuthShell({ title, subtitle, children, footer }: {
  title: string;
  subtitle: string;
  children: ReactNode;
  footer: ReactNode;
}) {
  return (
    <main className="auth-page" aria-labelledby="auth-title">
      <div className="auth-wordmark" aria-label="Contract Intelligence home">
        <span className="auth-logo">CI</span>
        <span>Contract Intelligence</span>
      </div>
      <section className="auth-card" aria-describedby="auth-subtitle">
        <header className="auth-heading">
          <h1 id="auth-title">{title}</h1>
          <p id="auth-subtitle">{subtitle}</p>
        </header>
        {children}
        <footer className="auth-footer">{footer}</footer>
      </section>
    </main>
  );
}

function Banner({ message, onDismiss }: { message: string | null; onDismiss: () => void }) {
  if (!message) return null;
  return (
    <div className="auth-banner" role="alert">
      <span>{message}</span>
      <button type="button" onClick={onDismiss} aria-label="Dismiss error">×</button>
    </div>
  );
}

function FieldError({ message }: { message?: string }) {
  if (!message) return null;
  return <p className="auth-field-error">{message}</p>;
}

function PasswordInput({
  id,
  value,
  autoComplete,
  onChange,
  onBlur,
  invalid,
}: {
  id: string;
  value: string;
  autoComplete: "current-password" | "new-password";
  onChange: (value: string) => void;
  onBlur: () => void;
  invalid?: boolean;
}) {
  const [visible, setVisible] = useState(false);
  return (
    <div className="password-control">
      <input
        id={id}
        type={visible ? "text" : "password"}
        value={value}
        onChange={(event) => onChange(event.target.value)}
        onBlur={onBlur}
        autoComplete={autoComplete}
        aria-invalid={invalid || undefined}
        required
      />
      <button
        type="button"
        className="password-toggle"
        onClick={() => setVisible((current) => !current)}
        aria-label={visible ? "Hide password" : "Show password"}
      >
        <EyeIcon hidden={!visible} />
      </button>
    </div>
  );
}

export function LoginScreen({ onSuccess }: { onSuccess: () => void }) {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [touched, setTouched] = useState<TouchedState>({});
  const [serverError, setServerError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const emailError = touched.email && !isValidEmail(email) ? "Enter a valid email address." : "";
  const passwordError = touched.password && !password ? "Enter your password." : "";
  const isValid = isValidEmail(email) && password.length > 0;

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setTouched({ email: true, password: true });
    if (!isValid || busy) return;

    setBusy(true);
    setServerError(null);
    try {
      await login(email.trim(), password);
      onSuccess();
    } catch (err) {
      if (err instanceof ApiError && err.status === 401) {
        setServerError("Incorrect email or password.");
      } else {
        setServerError("We couldn’t reach Contract Intelligence. Please try again.");
      }
    } finally {
      setBusy(false);
    }
  }

  return (
    <AuthShell
      title="Log in"
      subtitle="Continue to your contract review workspace."
      footer={<span>Don’t have an account? <a href="/signup">Sign up</a></span>}
    >
      <form className="auth-form" onSubmit={submit} noValidate>
        <Banner message={serverError} onDismiss={() => setServerError(null)} />
        <label className="auth-field" htmlFor="login-email">
          <span>Email</span>
          <input
            id="login-email"
            type="email"
            value={email}
            onChange={(event) => setEmail(event.target.value)}
            onBlur={() => setTouched((current) => ({ ...current, email: true }))}
            autoComplete="email"
            aria-invalid={Boolean(emailError) || undefined}
            required
          />
          <FieldError message={emailError} />
        </label>

        <label className="auth-field" htmlFor="login-password">
          <span className="auth-label-row">
            <span>Password</span>
            <a href="#forgot-password">Forgot password?</a>
          </span>
          <PasswordInput
            id="login-password"
            value={password}
            autoComplete="current-password"
            onChange={setPassword}
            onBlur={() => setTouched((current) => ({ ...current, password: true }))}
            invalid={Boolean(passwordError)}
          />
          <FieldError message={passwordError} />
        </label>

        <button className="auth-submit" type="submit" disabled={!isValid || busy}>
          {busy ? <Spinner /> : "Log in"}
        </button>
      </form>
    </AuthShell>
  );
}

export function SignupScreen({ onSuccess }: { onSuccess: () => void }) {
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [touched, setTouched] = useState<TouchedState>({});
  const [serverError, setServerError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const passwordChecks = useMemo(
    () => PASSWORD_RULES.map((rule) => ({ ...rule, passed: rule.test(password) })),
    [password]
  );
  const passwordValid = passwordChecks.every((rule) => rule.passed);
  const nameError = touched.name && name.trim().length < 2 ? "Enter your full name." : "";
  const emailError = touched.email && !isValidEmail(email) ? "Enter a valid email address." : "";
  const passwordError = touched.password && !passwordValid ? "Password needs to meet all requirements." : "";
  const isValid = name.trim().length >= 2 && isValidEmail(email) && passwordValid;

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setTouched({ name: true, email: true, password: true });
    if (!isValid || busy) return;

    setBusy(true);
    setServerError(null);
    try {
      await registerUser({ name: name.trim(), email: email.trim(), password });
      await login(email.trim(), password);
      onSuccess();
    } catch (err) {
      if (err instanceof ApiError && err.status === 409) {
        setServerError("This email is already registered. Log in instead.");
      } else if (err instanceof ApiError && err.status === 422) {
        setServerError(err.message || "Check your details and try again.");
      } else {
        setServerError("We couldn’t create your account. Please try again.");
      }
    } finally {
      setBusy(false);
    }
  }

  return (
    <AuthShell
      title="Create your account"
      subtitle="Start reviewing contracts with evidence-grounded AI."
      footer={<span>Already have an account? <a href="/">Log in</a></span>}
    >
      <form className="auth-form" onSubmit={submit} noValidate>
        <Banner message={serverError} onDismiss={() => setServerError(null)} />
        <label className="auth-field" htmlFor="signup-name">
          <span>Name</span>
          <input
            id="signup-name"
            type="text"
            value={name}
            onChange={(event) => setName(event.target.value)}
            onBlur={() => setTouched((current) => ({ ...current, name: true }))}
            autoComplete="name"
            aria-invalid={Boolean(nameError) || undefined}
            required
          />
          <FieldError message={nameError} />
        </label>

        <label className="auth-field" htmlFor="signup-email">
          <span>Email</span>
          <input
            id="signup-email"
            type="email"
            value={email}
            onChange={(event) => setEmail(event.target.value)}
            onBlur={() => setTouched((current) => ({ ...current, email: true }))}
            autoComplete="email"
            aria-invalid={Boolean(emailError) || undefined}
            required
          />
          <FieldError message={emailError} />
        </label>

        <label className="auth-field" htmlFor="signup-password">
          <span>Password</span>
          <PasswordInput
            id="signup-password"
            value={password}
            autoComplete="new-password"
            onChange={setPassword}
            onBlur={() => setTouched((current) => ({ ...current, password: true }))}
            invalid={Boolean(passwordError)}
          />
          <FieldError message={passwordError} />
        </label>

        <ul className="password-checklist" aria-label="Password requirements">
          {passwordChecks.map((rule) => (
            <li key={rule.id} className={rule.passed ? "passed" : ""}>
              <span aria-hidden="true">{rule.passed ? "✓" : "○"}</span>
              {rule.label}
            </li>
          ))}
        </ul>

        <button className="auth-submit" type="submit" disabled={!isValid || busy}>
          {busy ? <Spinner /> : "Create account"}
        </button>
      </form>
    </AuthShell>
  );
}
