import { Globe, Laptop, Settings, Wand2 } from "lucide-react";

import Link from "next/link";
import Image from "next/image";

import {
  Sidebar,
  SidebarContent,
  SidebarGroup,
  SidebarGroupContent,
  SidebarGroupLabel,
  SidebarHeader,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
} from "@/components/ui/sidebar";

// Menu items.
const items = [
  {
    title: "Home",
    href: "/",
    icon: Globe,
    variant: "default",
  },
  {
    title: "Scenario Dashboard",
    href: "/scenario",
    icon: Laptop,
    variant: "default",
  },

  {
    title: "Template Settings",
    href: "/template_settings",
    icon: Settings,
    variant: "default",
  },
  {
    title: "Optimizer Dashboard",
    href: "/optimizer",
    icon: Wand2,
    variant: "default",
  },
];

export function AppSidebar() {
  return (
    <Sidebar>
      <SidebarHeader>
        <Link href="/" className="flex items-center lg:mr-6">
          <Image src="/images/logo.svg" alt="logo" className=" w-24 h-8" width={96} height={32} />
        </Link>
      </SidebarHeader>
      <SidebarContent>
        <SidebarGroup>
          <SidebarGroupContent>
            <SidebarMenu>
              {items.map((item) => (
                <SidebarMenuItem key={item.title}>
                  <SidebarMenuButton asChild>
                    <a href={item.href}>
                      <item.icon />
                      <span>{item.title}</span>
                    </a>
                  </SidebarMenuButton>
                </SidebarMenuItem>
              ))}
            </SidebarMenu>
          </SidebarGroupContent>
        </SidebarGroup>
      </SidebarContent>
    </Sidebar>
  );
}
