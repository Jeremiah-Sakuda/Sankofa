"use client";

import { useEffect } from "react";

export default function GlobalError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    console.error("[Sankofa GlobalError]", error);
  }, [error]);

  return (
    <html lang="en">
      <body style={{ background: "#0D0D0D", color: "#F5EDDA", fontFamily: "Georgia, serif" }}>
        <div style={{
          minHeight: "100vh",
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          justifyContent: "center",
          padding: "1.5rem",
        }}>
          <h1 style={{ fontSize: "1.5rem", color: "#D4A843", letterSpacing: "0.1em", textTransform: "uppercase" }}>
            Something went wrong
          </h1>
          <p style={{ marginTop: "1rem", color: "#8B7D6B", textAlign: "center", maxWidth: "28rem" }}>
            Sankofa encountered a critical error. Please try refreshing the page.
          </p>
          <button
            type="button"
            onClick={reset}
            style={{
              marginTop: "2rem",
              padding: "0.75rem 2rem",
              border: "1px solid #D4A843",
              color: "#D4A843",
              background: "transparent",
              letterSpacing: "0.1em",
              textTransform: "uppercase",
              cursor: "pointer",
            }}
          >
            Try Again
          </button>
        </div>
      </body>
    </html>
  );
}
