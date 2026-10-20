"use client"

import { createContext, useContext, useEffect, useState } from "react"
import { createClient } from "@/utils/supabase/client"
import type { User } from "@supabase/supabase-js"

interface AuthState {
  user: User | null
  loading: boolean
  signIn: (username: string, password: string) => Promise<{ error: string | null }>
  resetPassword: (email: string) => Promise<{ error: string | null }>
  updateProfile: (name: string) => Promise<{ error: string | null }>
  signOut: () => Promise<void>
}

const AuthContext = createContext<AuthState | null>(null)

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null)
  const [loading, setLoading] = useState(true)
  const [supabase] = useState(createClient)
  const member = (account: User | null) => account && ["user", "admin"].includes(account.app_metadata?.role) && account.app_metadata?.status !== "disabled" ? account : null

  useEffect(() => {
    supabase.auth.getUser().then(({ data: { user } }) => {
      setUser(member(user))
      setLoading(false)
    })

    const { data: { subscription } } = supabase.auth.onAuthStateChange((_event, session) => {
      setUser(member(session?.user ?? null))
      setLoading(false)
    })

    return () => subscription.unsubscribe()
  }, [supabase])

  const signIn = async (username: string, password: string) => {
    const login = username.trim().toLowerCase()
    const email = login === "admin" ? "admin@insightpro.local" : login.includes("@") ? login : `${login}@test.insightpro.invalid`
    const { error } = await supabase.auth.signInWithPassword({ email, password })
    if (error) return { error: error.message }
    const { data: { user: account } } = await supabase.auth.getUser()
    if (!member(account)) {
      await supabase.auth.signOut()
      return { error: "当前账号尚未获得内测访问权限，请联系管理员。" }
    }
    return { error: null }
  }

  const resetPassword = async (email: string) => {
    const { error } = await supabase.auth.resetPasswordForEmail(email, {
      redirectTo: `${window.location.origin}/auth/reset-password`,
    })
    return { error: error?.message ?? null }
  }

  const signOut = async () => {
    const { data: { session } } = await supabase.auth.getSession()
    if (session?.access_token) {
      await fetch("/api/auth/agent/revoke", {
        method: "POST",
        headers: { Authorization: `Bearer ${session.access_token}` },
      }).catch(() => undefined)
    }
    await supabase.auth.signOut()
    setUser(null)
  }

  const updateProfile = async (name: string) => {
    const { data, error } = await supabase.auth.updateUser({ data: { name: name.trim().slice(0, 80) } })
    if (data.user) setUser(data.user)
    return { error: error?.message ?? null }
  }

  return <AuthContext.Provider value={{ user, loading, signIn, resetPassword, updateProfile, signOut }}>{children}</AuthContext.Provider>
}

export function useAuth() {
  const value = useContext(AuthContext)
  if (!value) throw new Error("useAuth must be used inside AuthProvider")
  return value
}
