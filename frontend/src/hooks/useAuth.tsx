"use client";

import { useState, useEffect, useCallback, createContext, useContext, ReactNode } from "react";
import { initializeApp, getApps, FirebaseApp } from "firebase/app";
import {
  getAuth,
  onAuthStateChanged,
  signInWithPopup,
  GoogleAuthProvider,
  signOut as firebaseSignOut,
  User as FirebaseUser,
  Auth,
} from "firebase/auth";
import { API_BASE } from "../lib/api";

// Firebase configuration - these are public client-side keys
const firebaseConfig = {
  apiKey: process.env.NEXT_PUBLIC_FIREBASE_API_KEY,
  authDomain: process.env.NEXT_PUBLIC_FIREBASE_AUTH_DOMAIN,
  projectId: process.env.NEXT_PUBLIC_FIREBASE_PROJECT_ID,
  storageBucket: process.env.NEXT_PUBLIC_FIREBASE_STORAGE_BUCKET,
  messagingSenderId: process.env.NEXT_PUBLIC_FIREBASE_MESSAGING_SENDER_ID,
  appId: process.env.NEXT_PUBLIC_FIREBASE_APP_ID,
};

// Initialize Firebase only once
let firebaseApp: FirebaseApp | null = null;
let firebaseAuth: Auth | null = null;

function getFirebaseApp(): FirebaseApp | null {
  if (typeof window === "undefined") return null;
  if (!firebaseConfig.apiKey) {
    console.warn("Firebase not configured - missing NEXT_PUBLIC_FIREBASE_API_KEY");
    return null;
  }
  if (!firebaseApp) {
    const apps = getApps();
    firebaseApp = apps.length > 0 ? apps[0] : initializeApp(firebaseConfig);
  }
  return firebaseApp;
}

function getFirebaseAuth(): Auth | null {
  if (!firebaseAuth) {
    const app = getFirebaseApp();
    if (app) {
      firebaseAuth = getAuth(app);
    }
  }
  return firebaseAuth;
}

export interface AuthUser extends FirebaseUser {
  getIdToken: () => Promise<string>;
}

interface AuthContextValue {
  user: AuthUser | null;
  isLoading: boolean;
  isConfigured: boolean;
  signInWithGoogle: () => Promise<void>;
  signOut: () => Promise<void>;
}

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<AuthUser | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isConfigured, setIsConfigured] = useState(false);

  useEffect(() => {
    const auth = getFirebaseAuth();
    if (!auth) {
      setIsLoading(false);
      return;
    }

    setIsConfigured(true);

    const unsubscribe = onAuthStateChanged(auth, async (firebaseUser) => {
      if (firebaseUser) {
        // Notify backend of login
        try {
          const token = await firebaseUser.getIdToken();
          await fetch(`${API_BASE}/api/auth/login`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ id_token: token }),
          });
        } catch (e) {
          console.error("Failed to sync auth with backend:", e);
        }
        setUser(firebaseUser as AuthUser);
      } else {
        setUser(null);
      }
      setIsLoading(false);
    });

    return () => unsubscribe();
  }, []);

  const signInWithGoogle = useCallback(async () => {
    const auth = getFirebaseAuth();
    if (!auth) {
      throw new Error("Firebase not configured");
    }

    const provider = new GoogleAuthProvider();
    provider.setCustomParameters({
      prompt: "select_account",
    });

    await signInWithPopup(auth, provider);
  }, []);

  const signOut = useCallback(async () => {
    const auth = getFirebaseAuth();
    if (!auth) return;

    // Notify backend
    if (user) {
      try {
        const token = await user.getIdToken();
        await fetch(`${API_BASE}/api/auth/logout`, {
          method: "POST",
          headers: {
            Authorization: `Bearer ${token}`,
          },
        });
      } catch (e) {
        console.error("Failed to notify backend of logout:", e);
      }
    }

    await firebaseSignOut(auth);
  }, [user]);

  return (
    <AuthContext.Provider
      value={{
        user,
        isLoading,
        isConfigured,
        signInWithGoogle,
        signOut,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth(): AuthContextValue {
  const context = useContext(AuthContext);
  if (!context) {
    // Return a default value for when AuthProvider isn't used
    return {
      user: null,
      isLoading: false,
      isConfigured: false,
      signInWithGoogle: async () => {
        throw new Error("AuthProvider not found");
      },
      signOut: async () => {},
    };
  }
  return context;
}
