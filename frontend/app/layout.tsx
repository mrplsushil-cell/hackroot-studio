import "./globals.css";
import type { Metadata, Viewport } from "next";
import { Toaster } from "react-hot-toast";

export const metadata: Metadata = {
  title: "Hackroot Studio — Create. Imagine. Generate.",
  description:
    "An AI-powered video creation studio. Generate professional videos from a single prompt.",
  applicationName: "Hackroot Studio",
  authors: [{ name: "Hackroot" }],
  openGraph: {
    title: "Hackroot Studio",
    description: "Create. Imagine. Generate.",
    type: "website",
  },
};

export const viewport: Viewport = {
  themeColor: "#080b14",
  width: "device-width",
  initialScale: 1,
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className="dark">
      <body className="min-h-screen antialiased">
        {children}
        <Toaster
          position="top-right"
          toastOptions={{
            style: {
              background: "rgba(15,19,32,0.95)",
              color: "#f7f8fa",
              border: "1px solid rgba(255,255,255,0.08)",
            },
          }}
        />
      </body>
    </html>
  );
}
