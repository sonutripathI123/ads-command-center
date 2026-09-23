import navConfig from "./nav.json";

export type NavItem = { slug: string; label: string; moduleId: string };
export type NavGroup = { label: string; items: NavItem[] };

export const NAV_GROUPS: NavGroup[] = navConfig.groups;
export const NAV_ITEMS: NavItem[] = NAV_GROUPS.flatMap((g) => g.items);

export function findSection(slug: string): NavItem | undefined {
  return NAV_ITEMS.find((i) => i.slug === slug);
}

export function hrefFor(item: NavItem): string {
  return item.slug ? `/${item.slug}` : "/";
}
