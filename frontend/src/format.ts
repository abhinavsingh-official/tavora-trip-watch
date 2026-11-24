/* Every price in the app is a raw float from the API - interpolating it
   directly gave inconsistent-looking decimals side by side (₹969.2 next
   to ₹5914.7 next to ₹406.72) since JS never pads a trailing zero. This
   is the one place that formats a rupee amount, so every screen matches. */
export function formatInr(value: number | null | undefined): string {
  if (value === null || value === undefined) return '-';
  return value.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}
