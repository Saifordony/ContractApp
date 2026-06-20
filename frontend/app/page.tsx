"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";

import { isAuthenticated } from "@/lib/api";

export default function Home() {
  const router = useRouter();
  useEffect(() => {
    router.replace(isAuthenticated() ? "/workspace" : "/login");
  }, [router]);
  return <div className="grid min-h-screen place-items-center text-slate-400">Loading…</div>;
}
