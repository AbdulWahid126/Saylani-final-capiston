import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "AI Trading Copilot — Intelligent Trading Analytics & Decision Support",
  description:
    "Institutional trading analytics, risk management, MT5 automatic journaling, and contextual AI decision support.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className="dark">
      <body className="bg-background text-text-primary min-h-screen font-sans antialiased overflow-hidden">
        {children}
      </body>
    </html>
  );
}
