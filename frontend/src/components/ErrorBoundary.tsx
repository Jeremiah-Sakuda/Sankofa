"use client";

import React, { Component, type ReactNode } from "react";

interface Props {
  children: ReactNode;
}

interface State {
  hasError: boolean;
  error: Error | null;
}

export default class ErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, info: React.ErrorInfo) {
    console.error("[ErrorBoundary]", error, info.componentStack);
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="min-h-screen flex flex-col items-center justify-center bg-[var(--night)] px-6">
          <h1 className="font-[family-name:var(--font-display)] text-2xl text-[var(--gold)] tracking-wider uppercase">
            Something went wrong
          </h1>
          <p className="mt-4 font-[family-name:var(--font-body)] text-[var(--muted)] text-center max-w-md">
            Sankofa encountered an unexpected error. Please try refreshing the page.
          </p>
          {this.state.error && (
            <p className="mt-3 font-[family-name:var(--font-body)] text-xs text-[var(--terracotta)] text-center max-w-md opacity-70">
              {this.state.error.message}
            </p>
          )}
          <button
            type="button"
            onClick={() => {
              this.setState({ hasError: false, error: null });
              window.location.href = "/";
            }}
            className="mt-8 px-8 py-3 border border-[var(--gold)] text-[var(--gold)] font-[family-name:var(--font-display)] tracking-wider uppercase hover:bg-[var(--gold)] hover:text-[var(--night)] transition-all cursor-pointer"
          >
            Start Over
          </button>
        </div>
      );
    }

    return this.props.children;
  }
}
