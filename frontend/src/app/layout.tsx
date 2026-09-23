import type { Metadata } from "next";
import { AppShell } from "@/shell/AppShell";
import "./globals.css";

export const metadata: Metadata = {
  title: "PPC Command Center",
  description: "AI Google Ads Specialist for the chauffeur business",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html lang="en-AU" className="h-full antialiased">
      <body className="min-h-full">
        <AppShell>{children}</AppShell>
      </body>
    </html>
  );
}
