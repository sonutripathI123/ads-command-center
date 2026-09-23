// P04 — Ads Accounts (overrides the P01 [section] placeholder).
import { Suspense } from "react";
import { AdsAccountsPage } from "@/modules/ads-connection";

export default function Page() {
  return (
    <Suspense>
      <AdsAccountsPage />
    </Suspense>
  );
}
