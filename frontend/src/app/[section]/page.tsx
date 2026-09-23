// P01 — fallback route for every section whose module has no page yet.
// When a module builds its page it adds frontend/src/app/<slug>/page.tsx, which takes precedence
// over this dynamic route — the shell does not need to change.
import { notFound } from "next/navigation";
import { ModulePlaceholder } from "@/shell/ModulePlaceholder";
import { NAV_ITEMS, findSection } from "@/shell/nav";

export function generateStaticParams() {
  return NAV_ITEMS.filter((i) => i.slug).map((i) => ({ section: i.slug }));
}

export const dynamicParams = false;

export default async function SectionPage({ params }: PageProps<"/[section]">) {
  const { section } = await params;
  const item = findSection(section);
  if (!item) notFound();
  return <ModulePlaceholder item={item} />;
}
