import type { Metadata } from "next";

import "./globals.css";

export const metadata: Metadata = {
  title: "HireFlow AI",
  description: "Intelligent hiring operations for modern recruiting teams.",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body className="antialiased">{children}</body>
    </html>
  );
}
