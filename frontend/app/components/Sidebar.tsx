"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

import { UploadCloud, FileText } from "lucide-react";

export default function Sidebar() {
    const pathname = usePathname();

    const menu = [
        {
            name: "CV Screening",
            icon: UploadCloud,
            path: "/dashboard",
        },
        {
            name: "Resume Viewer",
            icon: FileText,
            path: "/resume-viewer",
        },
    ];

    return (
        <aside className="w-72 bg-white border-r border-slate-200 flex flex-col min-h-screen">
            <div>
                {/* Logo Section */}
                <div className="p-6 border-b border-slate-100">
                    {/* Logo (full width container, left aligned inside) */}
                    <div className="w-full flex items-center">
                        <img
                            src="/MedcubeUSA.png"
                            alt="MedcubeUSALogo"
                            className="h-10 w-auto object-contain"
                        />
                    </div>

                    {/* Text below logo */}
                    <p className="text-sm text-slate-500 mt-2">
                        TalentDesk Admin Portal
                    </p>
                </div>

                {/* Menu */}
                <nav className="p-4 space-y-3">
                    {menu.map((item) => {
                        const Icon = item.icon;
                        const active = pathname === item.path;

                        return (
                            <Link
                                key={item.path}
                                href={item.path}
                                className={`w-full flex items-center gap-3 px-4 py-3 rounded-xl transition
                ${active
                                        ? "bg-cyan-600 text-white"
                                        : "text-slate-700 hover:bg-slate-100"
                                    }`}
                            >
                                <Icon size={20} />
                                {item.name}
                            </Link>
                        );
                    })}
                </nav>
            </div>
        </aside>
    );
}