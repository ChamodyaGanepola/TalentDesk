"use client";

import { ToastProvider } from "@/app/components/ui/Toast";
import { AuthProvider } from "@/app/providers/AuthProvider";

export default function AppProviders({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <ToastProvider>
      <AuthProvider>{children}</AuthProvider>
    </ToastProvider>
  );
}
