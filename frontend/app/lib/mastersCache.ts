import { apiFetch, getApiBase } from "@/app/lib/api";
import { getAuthHeaders } from "@/app/lib/auth";

type MastersData = {
  skills: string[];
  qualifications: string[];
  professions: string[];
};

const EMPTY_MASTERS: MastersData = {
  skills: [],
  qualifications: [],
  professions: [],
};

let cache: MastersData | null = null;
let inflight: Promise<MastersData> | null = null;

export function isMastersCached(): boolean {
  return cache !== null;
}

export function isMastersLoading(): boolean {
  return inflight !== null;
}

export function getCachedMasters(): MastersData | null {
  return cache;
}

export async function fetchMasters(force = false): Promise<MastersData> {
  if (!force && cache) return cache;
  if (!force && inflight) return inflight;

  inflight = (async () => {
    if (!getApiBase()) {
      return EMPTY_MASTERS;
    }

    try {
      const [skillsRes, qualificationsRes, professionsRes] = await Promise.all([
        apiFetch("/skills", { headers: getAuthHeaders() }),
        apiFetch("/qualifications", { headers: getAuthHeaders() }),
        apiFetch("/professions", { headers: getAuthHeaders() }),
      ]);

      if (!skillsRes?.ok || !qualificationsRes?.ok) {
        return cache ?? EMPTY_MASTERS;
      }

      const [skills, qualifications] = await Promise.all([
        skillsRes.json(),
        qualificationsRes.json(),
      ]);

      let professions: string[] = cache?.professions ?? [];
      if (professionsRes?.ok) {
        professions = (await professionsRes.json()) || [];
      }

      cache = {
        skills: skills || [],
        qualifications: qualifications || [],
        professions: professions || [],
      };

      return cache;
    } catch {
      return cache ?? EMPTY_MASTERS;
    }
  })();

  try {
    return await inflight;
  } finally {
    inflight = null;
  }
}

export function prefetchMasters(): void {
  if (cache || inflight) return;
  void fetchMasters().catch(() => {
    // Ignore background prefetch failures.
  });
}

export function addSkillToCache(name: string): void {
  if (!cache) return;
  if (!cache.skills.includes(name)) {
    cache = {
      ...cache,
      skills: [...cache.skills, name].sort(),
    };
  }
}

export function addQualificationToCache(name: string): void {
  if (!cache) return;
  if (!cache.qualifications.includes(name)) {
    cache = {
      ...cache,
      qualifications: [...cache.qualifications, name].sort(),
    };
  }
}

export function addProfessionToCache(name: string): void {
  if (!cache) return;
  const exists = cache.professions.some(
    (p) => p.toLowerCase() === name.toLowerCase()
  );
  if (!exists) {
    cache = {
      ...cache,
      professions: [...cache.professions, name].sort((a, b) =>
        a.localeCompare(b)
      ),
    };
  }
}
