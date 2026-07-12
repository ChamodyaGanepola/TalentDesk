"use client";

import { useEffect, useRef, useState } from "react";
import { usePathname } from "next/navigation";
import { LogOut } from "lucide-react";

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
  const [open, setOpen] = useState(false);
  const menuRef = useRef<HTMLDivElement>(null);

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

  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (menuRef.current && !menuRef.current.contains(event.target as Node)) {
        setOpen(false);
      }
    }

    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  const handleLogout = () => {
    localStorage.removeItem("user");
    window.location.href = "/";
  };

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
        <div className="relative" ref={menuRef}>
          <button
            type="button"
            title={email}
            onClick={() => setOpen((prev) => !prev)}
            className="w-10 h-10 rounded-full bg-cyan-600 text-white flex items-center justify-center font-semibold cursor-pointer hover:bg-cyan-700 transition"
            aria-expanded={open}
            aria-haspopup="menu"
          >
            {initial}
          </button>

          {open && (
            <div
              role="menu"
              className="absolute right-0 top-12 w-64 bg-white border border-slate-200 rounded-2xl shadow-lg z-50 overflow-hidden"
            >
              <div className="px-4 py-3 border-b border-slate-100">
                <div className="font-medium text-slate-800 truncate">{name}</div>
                <div className="text-sm text-slate-500 truncate">{email}</div>
              </div>

              <div className="p-2">
                <button
                  type="button"
                  role="menuitem"
                  onClick={handleLogout}
                  className="w-full flex items-center gap-3 px-3 py-2.5 rounded-xl text-red-600 hover:bg-red-50 transition"
                >
                  <LogOut size={18} />
                  Logout
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
