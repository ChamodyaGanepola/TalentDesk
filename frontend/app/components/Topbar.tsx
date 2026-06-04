"use client";

import { useEffect, useState } from "react";
import { Bell, Search } from "lucide-react";
import { usePathname } from "next/navigation";

export default function Topbar() {
  const pathname = usePathname();

  const [notifications, setNotifications] = useState<string[]>([]);
  const [open, setOpen] = useState(false);
  const [unreadCount, setUnreadCount] = useState(0);

 {/* WS Connection for Notifications */}
 {/*
  useEffect(() => {
    const ws = new WebSocket("ws://localhost:8000/ws/dashboard");
  
    ws.onopen = () => console.log("WS Connected");

    ws.onmessage = (event) => {
      const data = JSON.parse(event.data);
      console.log("WS Message:", data);

      if (data.event === "excel_exported") {
        setNotifications((prev) => [
          ` Excel exported: ${data.file}`,
          ...prev,
        ]);
        setUnreadCount((prev) => prev + 1); // increment unread
      }
    };

    ws.onerror = (e) => console.log("WS Error", e);
    ws.onclose = () => console.log("WS Closed");

    return () => ws.close();
  }, []);

  // Clear unread count when dropdown opens
  useEffect(() => {
    if (open) {
      setUnreadCount(0); // mark all as read
    }
  }, [open]);
*/}
  return (
    <div className="relative bg-white rounded-2xl shadow-sm p-4 flex items-center justify-between mb-8">
      {/* Left */}
      <div>
        <h2 className="text-2xl font-bold text-slate-800">
          {pathname === "/dashboard"
            ? "CV Screening Dashboard"
            : "Admin Panel"}
        </h2>
      </div>

      {/* Right */}
      <div className="flex items-center gap-4">
        {/* Search */}
        {/*
        <div className="flex items-center gap-2 bg-slate-100 px-4 py-2 rounded-xl">
          <Search size={18} className="text-slate-400" />
          <input className="bg-transparent outline-none text-sm" />
        </div>
*/}
        {/* Bell */}
        {/*
        <div className="relative">
          <div
            className="w-10 h-10 rounded-full bg-slate-100 flex items-center justify-center cursor-pointer"
            onClick={() => setOpen(!open)}
          >
            <Bell size={18} />
            {unreadCount > 0 && (
              <span className="absolute top-0 right-0 w-3 h-3 bg-red-500 rounded-full animate-pulse"></span>
            )}
          </div>
*/}

          {/* Dropdown */}
          {/*
          {open && (
            <div className="absolute right-0 mt-2 w-80 bg-white shadow-lg rounded-xl border z-50">
              <div className="p-2 border-b font-semibold">
                Notifications
              </div>

              {notifications.length === 0 ? (
                <div className="p-3 text-sm text-slate-500">
                  No notifications
                </div>
              ) : (
                notifications.map((n, i) => (
                  <div
                    key={i}
                    className="p-3 text-sm border-b hover:bg-slate-50"
                  >
                    {n}
                  </div>
                ))
              )}
            </div>
          )}
        </div>
        */}

        {/* Profile */}
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-full bg-cyan-600 text-white flex items-center justify-center font-semibold">
            A
          </div>
        </div>
      </div>
    </div>
  );
}