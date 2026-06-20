"use client";

import { useRouter } from "next/navigation";
import { SignupScreen } from "@/components/auth/AuthScreens";

export default function SignupPage() {
  const router = useRouter();
  return <SignupScreen onSuccess={() => router.push("/")} />;
}
