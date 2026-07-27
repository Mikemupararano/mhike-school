import type { Metadata } from "next";

import "./globals.css";

import { brand } from "@/lib/brand";
import { AuthProvider } from "@/providers/AuthProvider";

function getMetadataBase(): URL {
  const configuredUrl =
    process.env.NEXT_PUBLIC_APP_URL ??
    process.env.APP_URL ??
    "http://localhost:3000";

  try {
    return new URL(configuredUrl);
  } catch {
    return new URL("http://localhost:3000");
  }
}

export const metadata: Metadata = {
  metadataBase: getMetadataBase(),

  title: {
    default: brand.name,
    template: `%s | ${brand.name}`,
  },

  description: brand.description,

  applicationName: brand.name,

  icons: {
    icon: "/logo-icon.svg",
    shortcut: "/logo-icon.svg",
    apple: "/apple-touch-icon.png",
  },

  openGraph: {
    type: "website",
    title: brand.name,
    description: brand.description,
    siteName: brand.name,
    images: [
      {
        url: "/og-image.png",
        alt: brand.name,
      },
    ],
  },

  twitter: {
    card: "summary_large_image",
    title: brand.name,
    description: brand.description,
    images: ["/og-image.png"],
  },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body
        style={{
          margin: 0,
          fontFamily: "Inter, Arial, sans-serif",
          background: "#f8fafc",
          minHeight: "100vh",
        }}
      >
        <AuthProvider>{children}</AuthProvider>
      </body>
    </html>
  );
}