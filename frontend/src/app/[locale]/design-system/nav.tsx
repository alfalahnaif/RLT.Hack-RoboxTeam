import { BuildingIcon, DesignToolsIcon, HistoryIcon, LifebuoyIcon, ListTreeIcon, SearchIcon, SettingsIcon, TableIcon } from "@/components/icons";
import { Badge } from "@/components/ui/badge";
import type { NavItem } from "@/components/layout/types";

/** Sample navigation for the gallery shell, shaped after the Supplier Radar screen inventory (docs/product/SCREENS.md). */
export const sampleNav: NavItem[] = [
  { key: "search", label: "Search", icon: SearchIcon, href: "/search", inBottomBar: true },
  { key: "results", label: "Results", icon: ListTreeIcon, href: "/results", inBottomBar: true },
  { key: "suppliers", label: "Suppliers", icon: BuildingIcon, href: "/suppliers", inBottomBar: true },
  { key: "compare", label: "Compare", icon: TableIcon, href: "/compare", badge: <Badge color="info" size="sm">New</Badge> },
  { key: "history", label: "Search history", icon: HistoryIcon, href: "/history" },
  {
    key: "settings",
    label: "Settings",
    icon: SettingsIcon,
    children: [
      { key: "sources", label: "Data sources", href: "/settings/sources" },
      { key: "ranking", label: "Ranking config", href: "/settings/ranking" },
    ],
  },
  { key: "design-system", label: "Design system", icon: DesignToolsIcon, href: "/design-system", inBottomBar: true },
];

export const sampleFooterNav: NavItem[] = [{ key: "help", label: "Help", icon: LifebuoyIcon, href: "/help" }];
