import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";
import { ToastContainer } from "@/components/ui/Toast";

const inter = Inter({ subsets: ["latin"] });

export const metadata: Metadata = {
  title: "ClipFlow - AI Video Editor",
  description: "AI-powered video editing that auto-removes filler words, dead air, and repeated takes",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className={`${inter.className} h-full`}>
      <body className="min-h-full bg-gray-950 text-gray-100">
        {children}
        <ToastContainer />
      </body>
    </html>
  );
}
