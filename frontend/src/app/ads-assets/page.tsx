// P09 — Ads & Assets (overrides the P01 [section] placeholder).
import { Suspense } from "react";
import { CreativesPage } from "@/modules/creatives";

export default function Page() {
  return <Suspense><CreativesPage /></Suspense>;
}
