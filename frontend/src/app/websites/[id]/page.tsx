// P03 — one website.
import { WebsiteDetail } from "@/modules/websites";

export default async function Page({ params }: PageProps<"/websites/[id]">) {
  const { id } = await params;
  return <WebsiteDetail id={Number(id)} />;
}
