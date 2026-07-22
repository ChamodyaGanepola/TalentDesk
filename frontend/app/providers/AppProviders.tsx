"use client";

import { ToastProvider } from "@/app/components/ui/Toast";

export default function AppProviders({
  children,
}: {
  children: React.ReactNode;
}) {
  return <ToastProvider>{children}</ToastProvider>;
}
