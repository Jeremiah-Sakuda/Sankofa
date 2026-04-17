"use client";

import { useState, useEffect } from "react";
import { motion, AnimatePresence } from "motion/react";
import SankofaBird from "./SankofaBird";
import { API_BASE } from "../lib/api";
import { useAuth } from "../hooks/useAuth";

interface ShareModalProps {
  isOpen: boolean;
  onClose: () => void;
  sessionId: string;
  familyName?: string;
  region?: string;
}

export default function ShareModal({
  isOpen,
  onClose,
  sessionId,
  familyName,
  region,
}: ShareModalProps) {
  const { user } = useAuth();
  const [shareUrl, setShareUrl] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    if (!isOpen) return;

    const createShareLink = async () => {
      setIsLoading(true);
      setError(null);

      try {
        const headers: Record<string, string> = {};

        // Include auth token for owned narratives
        if (user) {
          const token = await user.getIdToken();
          headers["Authorization"] = `Bearer ${token}`;
        }

        const res = await fetch(`${API_BASE}/api/narratives/${sessionId}/share`, {
          method: "POST",
          headers,
        });

        if (res.ok) {
          const data = await res.json();
          setShareUrl(data.share_url);
        } else {
          const err = await res.json().catch(() => ({}));
          setError(err.detail || "Failed to create share link");
        }
      } catch (e) {
        setError("Failed to create share link");
      } finally {
        setIsLoading(false);
      }
    };

    createShareLink();
  }, [isOpen, sessionId, user]);

  const handleCopy = async () => {
    if (!shareUrl) return;
    try {
      await navigator.clipboard.writeText(shareUrl);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      // Fallback for older browsers
      const textarea = document.createElement("textarea");
      textarea.value = shareUrl;
      document.body.appendChild(textarea);
      textarea.select();
      document.execCommand("copy");
      document.body.removeChild(textarea);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  const handleShareTwitter = () => {
    if (!shareUrl) return;
    const text = `I discovered my ${familyName || "family"} heritage from ${region || "my ancestral homeland"} through Sankofa. Explore your own roots:`;
    const url = `https://twitter.com/intent/tweet?text=${encodeURIComponent(text)}&url=${encodeURIComponent(shareUrl)}`;
    window.open(url, "_blank", "noopener,noreferrer");
  };

  const handleShareFacebook = () => {
    if (!shareUrl) return;
    const url = `https://www.facebook.com/sharer/sharer.php?u=${encodeURIComponent(shareUrl)}`;
    window.open(url, "_blank", "noopener,noreferrer");
  };

  const handleShareWhatsApp = () => {
    if (!shareUrl) return;
    const text = `I discovered my ${familyName || "family"} heritage through Sankofa! Check out my story: ${shareUrl}`;
    const url = `https://wa.me/?text=${encodeURIComponent(text)}`;
    window.open(url, "_blank", "noopener,noreferrer");
  };

  return (
    <AnimatePresence>
      {isOpen && (
        <motion.div
          className="fixed inset-0 z-50 flex items-center justify-center p-4"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
        >
          {/* Backdrop */}
          <motion.div
            className="absolute inset-0 bg-black/70 backdrop-blur-sm"
            onClick={onClose}
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
          />

          {/* Modal */}
          <motion.div
            className="relative bg-[var(--night)] border border-[var(--gold)]/30 rounded-lg p-8 max-w-md w-full shadow-2xl"
            initial={{ scale: 0.9, opacity: 0, y: 20 }}
            animate={{ scale: 1, opacity: 1, y: 0 }}
            exit={{ scale: 0.9, opacity: 0, y: 20 }}
            transition={{ type: "spring", duration: 0.5 }}
          >
            {/* Close button */}
            <button
              onClick={onClose}
              className="absolute top-4 right-4 text-[var(--muted)] hover:text-[var(--ivory)] transition-colors cursor-pointer"
            >
              <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <line x1="18" y1="6" x2="6" y2="18" />
                <line x1="6" y1="6" x2="18" y2="18" />
              </svg>
            </button>

            {/* Content */}
            <div className="text-center">
              <SankofaBird className="w-12 h-12 text-[var(--gold)] mx-auto mb-4" />

              <h2 className="font-[family-name:var(--font-display)] text-2xl text-[var(--gold)] tracking-wider mb-2">
                Share Your Story
              </h2>

              <p className="font-[family-name:var(--font-body)] text-[var(--muted)] text-sm mb-6">
                Let others discover the heritage of the {familyName || "your"} family.
              </p>

              {isLoading && (
                <div className="flex justify-center py-8">
                  <div className="w-8 h-8 border-2 border-[var(--gold)]/30 border-t-[var(--gold)] rounded-full animate-spin" />
                </div>
              )}

              {error && (
                <p className="text-[var(--terracotta)] text-sm mb-4 font-[family-name:var(--font-body)]">
                  {error}
                </p>
              )}

              {shareUrl && (
                <>
                  {/* URL display and copy */}
                  <div className="mb-6">
                    <div className="flex items-center gap-2 bg-black/30 border border-[var(--gold)]/20 rounded-lg p-3">
                      <input
                        type="text"
                        readOnly
                        value={shareUrl}
                        className="flex-1 bg-transparent text-[var(--ivory)] text-sm font-[family-name:var(--font-body)] outline-none"
                      />
                      <button
                        onClick={handleCopy}
                        className="px-3 py-1 bg-[var(--gold)] text-[var(--night)] font-[family-name:var(--font-display)] text-xs tracking-wider uppercase rounded hover:bg-[var(--gold)]/80 transition-colors cursor-pointer"
                      >
                        {copied ? "Copied!" : "Copy"}
                      </button>
                    </div>
                  </div>

                  {/* Social share buttons */}
                  <div className="flex items-center justify-center gap-4">
                    <button
                      onClick={handleShareTwitter}
                      className="w-12 h-12 rounded-full bg-[#1DA1F2]/10 border border-[#1DA1F2]/30 text-[#1DA1F2] flex items-center justify-center hover:bg-[#1DA1F2]/20 transition-colors cursor-pointer"
                      title="Share on Twitter"
                    >
                      <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="currentColor">
                        <path d="M18.244 2.25h3.308l-7.227 8.26 8.502 11.24H16.17l-5.214-6.817L4.99 21.75H1.68l7.73-8.835L1.254 2.25H8.08l4.713 6.231zm-1.161 17.52h1.833L7.084 4.126H5.117z"/>
                      </svg>
                    </button>

                    <button
                      onClick={handleShareFacebook}
                      className="w-12 h-12 rounded-full bg-[#1877F2]/10 border border-[#1877F2]/30 text-[#1877F2] flex items-center justify-center hover:bg-[#1877F2]/20 transition-colors cursor-pointer"
                      title="Share on Facebook"
                    >
                      <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="currentColor">
                        <path d="M24 12.073c0-6.627-5.373-12-12-12s-12 5.373-12 12c0 5.99 4.388 10.954 10.125 11.854v-8.385H7.078v-3.47h3.047V9.43c0-3.007 1.792-4.669 4.533-4.669 1.312 0 2.686.235 2.686.235v2.953H15.83c-1.491 0-1.956.925-1.956 1.874v2.25h3.328l-.532 3.47h-2.796v8.385C19.612 23.027 24 18.062 24 12.073z"/>
                      </svg>
                    </button>

                    <button
                      onClick={handleShareWhatsApp}
                      className="w-12 h-12 rounded-full bg-[#25D366]/10 border border-[#25D366]/30 text-[#25D366] flex items-center justify-center hover:bg-[#25D366]/20 transition-colors cursor-pointer"
                      title="Share on WhatsApp"
                    >
                      <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="currentColor">
                        <path d="M17.472 14.382c-.297-.149-1.758-.867-2.03-.967-.273-.099-.471-.148-.67.15-.197.297-.767.966-.94 1.164-.173.199-.347.223-.644.075-.297-.15-1.255-.463-2.39-1.475-.883-.788-1.48-1.761-1.653-2.059-.173-.297-.018-.458.13-.606.134-.133.298-.347.446-.52.149-.174.198-.298.298-.497.099-.198.05-.371-.025-.52-.075-.149-.669-1.612-.916-2.207-.242-.579-.487-.5-.669-.51-.173-.008-.371-.01-.57-.01-.198 0-.52.074-.792.372-.272.297-1.04 1.016-1.04 2.479 0 1.462 1.065 2.875 1.213 3.074.149.198 2.096 3.2 5.077 4.487.709.306 1.262.489 1.694.625.712.227 1.36.195 1.871.118.571-.085 1.758-.719 2.006-1.413.248-.694.248-1.289.173-1.413-.074-.124-.272-.198-.57-.347m-5.421 7.403h-.004a9.87 9.87 0 01-5.031-1.378l-.361-.214-3.741.982.998-3.648-.235-.374a9.86 9.86 0 01-1.51-5.26c.001-5.45 4.436-9.884 9.888-9.884 2.64 0 5.122 1.03 6.988 2.898a9.825 9.825 0 012.893 6.994c-.003 5.45-4.437 9.884-9.885 9.884m8.413-18.297A11.815 11.815 0 0012.05 0C5.495 0 .16 5.335.157 11.892c0 2.096.547 4.142 1.588 5.945L.057 24l6.305-1.654a11.882 11.882 0 005.683 1.448h.005c6.554 0 11.89-5.335 11.893-11.893a11.821 11.821 0 00-3.48-8.413z"/>
                      </svg>
                    </button>
                  </div>
                </>
              )}

              <p className="mt-6 text-xs text-[var(--muted)]/60 font-[family-name:var(--font-body)]">
                Anyone with this link can view your story in read-only mode.
              </p>
            </div>
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
