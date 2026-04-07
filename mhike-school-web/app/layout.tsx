import "./globals.css";
import { AuthProvider } from "@/providers/AuthProvider";

export const metadata = {
  title: "Mhike School",
  description: "Mhike School LMS platform",
  icons: {
    icon: "/branding/favicon.png",
    shortcut: "/branding/favicon.png",
    apple: "/branding/icon.png",
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
        }}
      >
        <AuthProvider>{children}</AuthProvider>
      </body>
    </html>
  );
}