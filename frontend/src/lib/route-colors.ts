// Route palette shared by the map lines and the result list (docs/DESIGN.md §2.1).
export const ROUTE_COLORS = ["#3B82F6", "#10B981", "#F59E0B", "#06B6D4", "#EF4444"];

export const routeColor = (index: number): string => ROUTE_COLORS[index % ROUTE_COLORS.length];
