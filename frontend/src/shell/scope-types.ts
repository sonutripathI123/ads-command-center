// P01 — scope data contract. A loader (supplied by app/ShellFrame.tsx, implemented by P03) fills it.
export type Website = { id: string; name: string; domain: string; service: string; location: string; adsAccountId: string | null };
export type AdsAccount = { id: string; name: string; customerId: string };
export type ScopeData = { websites: Website[]; adsAccounts: AdsAccount[] };
export type ScopeLoader = () => Promise<ScopeData>;
