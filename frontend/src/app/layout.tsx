import type { Metadata } from "next";
import { ShellFrame } from "./ShellFrame";
import "./globals.css";

export const metadata: Metadata = {
  title: "PPC Command Center",
  description: "AI Google Ads Specialist for the chauffeur business",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html lang="en-AU" className="h-full antialiased">
      <body className="min-h-full" suppressHydrationWarning>
        <ShellFrame>{children}</ShellFrame>
      </body>
    </html>
  );
}
