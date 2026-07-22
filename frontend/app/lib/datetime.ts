/** Sri Lanka (Asia/Colombo) date/time helpers */

export const SL_TIMEZONE = "Asia/Colombo";

/** Treat naive backend timestamps as UTC. */
export function parseServerDate(value: string | null | undefined): Date | null {
  if (!value) return null;

  const raw = value.trim();
  if (!raw) return null;

  const hasZone = /([zZ]|[+-]\d{2}:?\d{2})$/.test(raw);
  const date = new Date(hasZone ? raw : `${raw}Z`);

  if (Number.isNaN(date.getTime())) return null;
  return date;
}

export function formatSLDate(value: string | null | undefined): string {
  const date = parseServerDate(value);
  if (!date) return "Unknown date";

  return new Intl.DateTimeFormat("en-LK", {
    timeZone: SL_TIMEZONE,
    year: "numeric",
    month: "short",
    day: "2-digit",
  }).format(date);
}

export function formatSLTime(value: string | null | undefined): string {
  const date = parseServerDate(value);
  if (!date) return "--:--";

  return new Intl.DateTimeFormat("en-LK", {
    timeZone: SL_TIMEZONE,
    hour: "2-digit",
    minute: "2-digit",
    hour12: true,
  }).format(date);
}

export function formatSLDateTime(value: string | null | undefined): string {
  const date = parseServerDate(value);
  if (!date) return "-";

  return new Intl.DateTimeFormat("en-LK", {
    timeZone: SL_TIMEZONE,
    year: "numeric",
    month: "short",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    hour12: true,
  }).format(date);
}

/** YYYY-MM-DD key in Sri Lankan calendar day */
export function toSLDateKey(value: string | null | undefined): string {
  const date = parseServerDate(value);
  if (!date) return "";

  return new Intl.DateTimeFormat("en-CA", {
    timeZone: SL_TIMEZONE,
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
  }).format(date);
}

export function formatExperienceYearsMonths(totalYears: number | null | undefined): string {
  /** @deprecated Prefer formatExperienceFromMonths — years input for legacy only */
  const value = Number(totalYears || 0);
  if (!Number.isFinite(value) || value < 0) return "0 months";

  const totalMonths = Math.round(value * 12);
  return formatExperienceFromMonths(totalMonths);
}

/** Convert stored months → "X years Y months" for UI display */
export function formatExperienceFromMonths(
  totalMonths: number | null | undefined
): string {
  let months = Math.round(Number(totalMonths || 0));
  if (!Number.isFinite(months) || months < 0) months = 0;

  const years = Math.floor(months / 12);
  const rem = months % 12;

  const yLabel = years === 1 ? "1 year" : `${years} years`;
  const mLabel = rem === 1 ? "1 month" : `${rem} months`;

  if (years === 0 && rem === 0) return "0 months";
  if (years === 0) return mLabel;
  if (rem === 0) return yLabel;
  return `${yLabel} ${mLabel}`;
}

export function yearsMonthsToValue(years: number, months: number): number {
  const y = Math.max(0, Math.floor(years || 0));
  const m = Math.min(11, Math.max(0, Math.floor(months || 0)));
  return Number((y + m / 12).toFixed(4));
}

export function yearsMonthsToTotalMonths(years: number, months: number): number {
  const y = Math.max(0, Math.floor(years || 0));
  const m = Math.min(11, Math.max(0, Math.floor(months || 0)));
  return y * 12 + m;
}
