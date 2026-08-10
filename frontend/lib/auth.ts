"use client";
import { create } from "zustand";
import { persist } from "zustand/middleware";
import { Token, User } from "./api";

type AuthState = {
  token: string | null;
  user: User | null;
  setAuth: (t: Token) => void;
  setUser: (u: User) => void;
  clear: () => void;
};

export const useAuth = create<AuthState>()(
  persist(
    (set) => ({
      token: null,
      user: null,
      setAuth: (t) => {
        if (typeof window !== "undefined") {
          window.localStorage.setItem("hackroot_token", t.access_token);
        }
        set({ token: t.access_token, user: t.user });
      },
      setUser: (u) => set({ user: u }),
      clear: () => {
        if (typeof window !== "undefined") {
          window.localStorage.removeItem("hackroot_token");
        }
        set({ token: null, user: null });
      },
    }),
    { name: "hackroot-auth" }
  )
);
