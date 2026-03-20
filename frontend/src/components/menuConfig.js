// =============================================================
// frontend/src/components/menuConfig.js
// Configuración de navegación por rol — RN-01
// =============================================================

import {
  Leaf,
  Thermometer,
  Brain,
  GitBranch,
  TrendingUp,
  FileText,
  LayoutDashboard,
  User,
} from "lucide-react";

export const MENU_ITEMS = [
  {
    key: "dashboard",
    label: "Dashboard",
    icon: LayoutDashboard,
    path: "/dashboard",
    roles: ["Administrador", "Caficultor", "Comercializador", "Productor"],
  },
  {
    key: "cultivos",
    label: "Cultivos",
    icon: Leaf,
    path: "/cultivos",
    roles: ["Administrador", "Caficultor"],
  },
  {
    key: "monitoreo",
    label: "Monitoreo",
    icon: Thermometer,
    path: "/monitoreo",
    roles: ["Administrador", "Caficultor"],
  },
  {
    key: "ia",
    label: "IA / Análisis",
    icon: Brain,
    path: "/ia",
    roles: ["Administrador", "Caficultor", "Productor"],
  },
  {
    key: "trazabilidad",
    label: "Trazabilidad",
    icon: GitBranch,
    path: "/trazabilidad",
    roles: ["Administrador", "Caficultor", "Comercializador", "Productor", "Consumidor"],
  },
  {
    key: "mercado",
    label: "Mercado",
    icon: TrendingUp,
    path: "/mercado",
    roles: ["Administrador", "Comercializador"],
  },
  {
    key: "reportes",
    label: "Reportes",
    icon: FileText,
    path: "/reportes",
    roles: ["Administrador", "Productor"],
  },
  {
    key: "perfil",
    label: "Perfil",
    icon: User,
    path: "/perfil",
    roles: ["Administrador", "Caficultor", "Comercializador", "Productor"],
  },
];

/**
 * Filtra los ítems del menú según el rol del usuario.
 * @param {string} rol - nombre_rol del usuario autenticado
 * @returns {Array} ítems visibles para ese rol
 */
export function getMenuPorRol(rol) {
  if (!rol) return [];
  return MENU_ITEMS.filter((item) => item.roles.includes(rol));
}
