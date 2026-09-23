// P01 MOCK DATA — replaced by P03 (websites) and P04 (ads accounts) via their public interfaces.
// Names/domains are placeholders, not real sites.

export type Website = { id: string; name: string; domain: string; service: string; location: string };
export type AdsAccount = { id: string; name: string; customerId: string };

export const MOCK_WEBSITES: Website[] = [
  { id: "w1", name: "Main Brand", domain: "main-brand.example", service: "Chauffeur", location: "Sydney" },
  { id: "w2", name: "Airport Transfers", domain: "airport-transfers.example", service: "Airport transfer", location: "Sydney" },
  { id: "w3", name: "Wedding Cars", domain: "wedding-cars.example", service: "Wedding", location: "Sydney" },
  { id: "w4", name: "Corporate Cars", domain: "corporate-cars.example", service: "Corporate", location: "Sydney" },
  { id: "w5", name: "Melbourne Chauffeurs", domain: "melbourne.example", service: "Chauffeur", location: "Melbourne" },
  { id: "w6", name: "Brisbane Chauffeurs", domain: "brisbane.example", service: "Chauffeur", location: "Brisbane" },
  { id: "w7", name: "Cruise Transfers", domain: "cruise-transfers.example", service: "Cruise transfer", location: "Sydney" },
  { id: "w8", name: "Tours & Events", domain: "tours-events.example", service: "Tours/events", location: "NSW" },
];

export const MOCK_ADS_ACCOUNTS: AdsAccount[] = [
  { id: "a1", name: "Primary Ads Account", customerId: "000-000-0001" },
  { id: "a2", name: "Interstate Ads Account", customerId: "000-000-0002" },
];

export const MOCK_ALERTS = [
  { id: "m1", level: "info" as const, text: "Demo data: websites and ads accounts are placeholders until P03/P04 are connected." },
];
