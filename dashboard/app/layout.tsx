import type { Metadata } from "next";
import { Comic_Relief } from "next/font/google";
import "./assets/main.css";

const comicRelief = Comic_Relief({
  variable: "--font-comic_relief",
  subsets: ["latin"],
  weight: ["400", "700"]
});

export const metadata: Metadata = {
  title: "Pothole Patrol",
  description: "Smarter maintenance starts with seeing the damage. Pothole Patrol helps cities fill the holes that matter!",
  icons: "/logo-minified.svg"
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html lang="en" className={`${comicRelief.variable} h-full antialiased`}>
      <body className="flex min-h-full flex-col">{children}</body>
    </html>
  );
}
