import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Contract Intelligence",
  description: "Evidence-grounded contract analysis",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
