"use client"

import { createContext, useContext, useEffect, useState } from "react"
import { createClient } from "@/utils/supabase/client"
import type { Session, User } from "@supabase/supabase-js"

interface AuthState {
  user: User | null
  session: Session | null
  loading: boolean
  isAuthenticated: boolean
  isAdmin: boolean
  signIn: (username: string, password: string) => Promise<{ error: string | null }>
  signOut: () => Promise<void>
}

const AuthContext = createContext<AuthState | null>(null)

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null)
  const [session, setSession] = useState<Session | null>(null)
  const [loading, setLoading] = useState(true)
  const [supabase] = useState(createClient)
  const member = (account: User | null) => account?.app_metadata?.role === "admin" && account.app_metadata?.status !== "disabled" ? account : null

  useEffect(() => {
    supabase.auth.getUser().then(async ({ data: { user } }) => {
      const admin = member(user)
      setUser(admin)
      setSession(admin ? (await supabase.auth.getSession()).data.session : null)
      if (user && !admin) await supabase.auth.signOut()
      setLoading(false)
    }).catch(() => { setUser(null); setSession(null); setLoading(false) })

    const { data: { subscription } } = supabase.auth.onAuthStateChange((event, session) => {
      if (event === "INITIAL_SESSION") return
      const admin = member(session?.user ?? null)
      setUser(admin)
      setSession(admin ? session : null)
      setLoading(false)
    })

    return () => subscription.unsubscribe()
  }, [supabase])

  const signIn = async (username: string, password: string) => {
    const login = username.trim().toLowerCase()
    const email = login.includes("@") ? login : `${login}@insightpro.local`
    const { error } = await supabase.auth.signInWithPassword({ email, password })
    if (error) return { error: error.message }
    const { data: { user: account } } = await supabase.auth.getUser()
    if (!member(account)) {
      await supabase.auth.signOut()
      return { error: "该账号无管理员权限。" }
    }
    return { error: null }
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
    setSession(null)
  }

  return <AuthContext.Provider value={{ user, session, loading, isAuthenticated: !!session, isAdmin: !!user, signIn, signOut }}>{children}</AuthContext.Provider>
}

export function useAuth() {
  const value = useContext(AuthContext)
  if (!value) throw new Error("useAuth must be used inside AuthProvider")
  return value
}
