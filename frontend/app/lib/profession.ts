const LEVEL_PREFIXES = [
  "mid-level",
  "mid level",
  "entry-level",
  "entry level",
  "principal",
  "associate",
  "senior",
  "junior",
  "staff",
  "lead",
  "snr",
  "sr.",
  "jr.",
  "sr",
  "jr",
] as const;

const LEAD_MANAGER_TITLES = new Set([
  "team lead",
  "tech lead",
  "technical lead",
  "engineering lead",
  "engineering manager",
  "software manager",
  "development manager",
  "dev manager",
  "project lead",
  "manager",
]);

const DEFAULT_INTERN_BASE = "Software Engineer";

function normalizeProfession(profession: string): string {
  return profession
    .trim()
    .replace(/[-_]+/g, " ")
    .replace(/\s+/g, " ")
    .toLowerCase();
}

function displayProfession(profession: string): string {
  const cleaned = normalizeProfession(profession);
  if (!cleaned) return "";
  const original = profession
    .trim()
    .replace(/[-_]+/g, " ")
    .replace(/\s+/g, " ");
  if (original.toLowerCase() === cleaned) return original;
  return cleaned
    .split(" ")
    .map((w) =>
      ["and", "of", "for"].includes(w) ? w : w.charAt(0).toUpperCase() + w.slice(1)
    )
    .join(" ");
}

function isLeadOrManagerTitle(lower: string): boolean {
  if (LEAD_MANAGER_TITLES.has(lower)) return true;
  if (
    lower.endsWith(" team lead") ||
    lower.endsWith(" tech lead") ||
    lower.endsWith(" technical lead") ||
    lower.endsWith(" engineering lead")
  ) {
    return true;
  }
  if (
    lower.endsWith(" manager") &&
    !lower.includes("engineer") &&
    !lower.includes("developer")
  ) {
    return true;
  }
  return false;
}

/** Hiring position → IC base used for intern labels. */
export function internBaseProfession(profession: string): string {
  let lower = normalizeProfession(profession);
  if (!lower) return "";

  for (const suffix of [" internship", " intern", " trainee"] as const) {
    if (lower.endsWith(suffix)) {
      lower = lower.slice(0, -suffix.length).trim();
      break;
    }
  }

  if (!lower || ["intern", "internship", "trainee"].includes(lower)) {
    return DEFAULT_INTERN_BASE;
  }

  if (isLeadOrManagerTitle(lower)) {
    return DEFAULT_INTERN_BASE;
  }

  let baseLower = lower;
  while (true) {
    let stripped = false;
    for (const prefix of LEVEL_PREFIXES) {
      const token = `${prefix} `;
      if (baseLower.startsWith(token)) {
        baseLower = baseLower.slice(token.length).trim();
        stripped = true;
        break;
      }
    }
    if (!stripped) break;
  }

  if (!baseLower || isLeadOrManagerTitle(baseLower)) {
    return DEFAULT_INTERN_BASE;
  }

  if (baseLower === "software engineer") {
    return DEFAULT_INTERN_BASE;
  }

  return displayProfession(baseLower) || DEFAULT_INTERN_BASE;
}

/**
 * Hiring position → related intern title.
 * Senior Software Engineer → Software Engineer Intern
 * Team Lead → Software Engineer Intern
 */
export function professionInternLabel(profession: string): string {
  const lower = normalizeProfession(profession);
  if (!lower) return "Intern";

  if (["intern", "internship", "trainee"].includes(lower)) {
    return "Intern";
  }

  const base = internBaseProfession(profession);
  return base ? `${base} Intern` : "Intern";
}
