import "./globals.css";
import { AuthProvider } from "@/providers/AuthProvider";
import { brand } from "@/lib/brand";

export const metadata = {
  title: brand.name,
  description: brand.description,
  icons: {
    icon: "/logo-icon.svg",
    shortcut: "/logo-icon.svg",
    apple: "/apple-touch-icon.png",
  },
  openGraph: {
    title: brand.name,
    description: brand.description,
    images: ["/og-image.png"],
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
}: {
  children: React.ReactNode;
}) {
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