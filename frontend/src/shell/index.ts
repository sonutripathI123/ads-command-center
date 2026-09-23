// P01 — public interface of the dashboard shell.
// Module pages (frontend/src/modules/<slug>) may import ONLY from "@/shell" (this file), never deeper.
export { useScope, SCOPE_ALL } from "./ScopeContext";
export { PageHeader } from "./PageHeader";
export { useModuleStatus } from "./ModuleStatus";
export { API_BASE } from "./api";
export type { Website, AdsAccount } from "./mock/scope";
