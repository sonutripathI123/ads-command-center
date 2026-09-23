"use client";
import { createContext, useContext } from "react";
import type { ModuleInfo } from "./api";

type ModuleStatus = { modules: ModuleInfo[] | null; loading: boolean };
const Ctx = createContext<ModuleStatus>({ modules: null, loading: true });

export const ModuleStatusProvider = Ctx.Provider;
export const useModuleStatus = () => useContext(Ctx);
