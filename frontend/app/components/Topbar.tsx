"use client";

import { useEffect, useState } from "react";
import { usePathname } from "next/navigation";

type User = {
  name?: string;
  email?: string;
};

function getPageTitle(pathname: string) {
  if (pathname === "/dashboard") return "CV Screening Dashboard";
  if (pathname === "/resume-viewer") return "Resume Viewer";
  return "Admin Panel";
}

export default function Topbar() {
  const pathname = usePathname();
  const [user, setUser] = useState<User | null>(null);

  useEffect(() => {
    try {
      const storedUser = localStorage.getItem("user");

      if (storedUser) {
        setUser(JSON.parse(storedUser));
      }
    } catch (error) {
      console.error("Failed to read user:", error);
    }
  }, []);

  const email = user?.email || "admin@gmail.com";
  const name = user?.name || "Admin";
  const initial = email.charAt(0).toUpperCase();

  return (
    <div className="relative bg-white rounded-2xl shadow-sm p-4 flex items-center justify-between mb-8">
      <div>
        <h2 className="text-2xl font-bold text-slate-800">
          {getPageTitle(pathname)}
        </h2>
      </div>

      <div className="flex items-center gap-4">
        <div className="relative group flex items-center gap-3">
          <div
            title={email}
            className="w-10 h-10 rounded-full bg-cyan-600 text-white flex items-center justify-center font-semibold cursor-pointer"
          >
            {initial}
          </div>

          <div className="absolute right-0 top-12 hidden group-hover:block bg-slate-900 text-white text-sm px-3 py-2 rounded-lg shadow-lg whitespace-nowrap z-50">
            <div className="font-medium">{name}</div>
            <div className="text-xs text-slate-300">{email}</div>
          </div>
        </div>
      </div>
    </div>
  );
}