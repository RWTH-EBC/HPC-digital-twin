import { ModeToggle } from "@/components/mode-toogle";
import { ThemeProvider } from "@/components/theme-provider";
import type { Metadata } from "next";
import { Inter } from "next/font/google";
import Link from "next/link";
import "./globals.css";

import { AppSidebar } from "@/components/app-sidebar";
import InfluxConnectionProvider from "@/components/influx-connection-provider";
import SSEConnectionProvider from "@/components/sse-connection-provider";
import { Separator } from "@/components/ui/separator";
import {
  SidebarInset,
  SidebarProvider,
  SidebarTrigger,
} from "@/components/ui/sidebar";

const inter = Inter({ subsets: ["latin"] });

export const metadata: Metadata = {
  title: "IT Zauber Dashboard",
  icons: [{ rel: "icon", url: "/images/favicon.ico" }],
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" suppressHydrationWarning={true}>
      <body className={inter.className}>
        <ThemeProvider
          attribute="class"
          defaultTheme="system"
          enableSystem
          disableTransitionOnChange
        >
          <SidebarProvider>
            <InfluxConnectionProvider>
              <SSEConnectionProvider>
                <AppSidebar />
                <SidebarInset>
                  <header className="flex h-16 shrink-0 items-center gap-2 transition-[width,height] ease-linear group-has-[[data-collapsible=icon]]/sidebar-wrapper:h-12">
                    <div className="flex items-center gap-2 px-4">
                      <SidebarTrigger className="-ml-1" />
                      <ModeToggle />
                      <Separator orientation="vertical" className="mr-2 h-4" />
                      <Link href="/" className="flex items-center gap-2">
                        <span className="text-nowrap">IT-Zauber Dashboard</span>
                      </Link>
                    </div>
                  </header>
                  <div className="container-wrapper">
                    <div className="m-4 mt-0">{children}</div>
                  </div>
                </SidebarInset>
              </SSEConnectionProvider>
            </InfluxConnectionProvider>
          </SidebarProvider>
        </ThemeProvider>
      </body>
    </html>
  );
}
