import { getAuthHeaders } from "@/app/lib/auth";

const API = process.env.NEXT_PUBLIC_API_URL;

type MastersData = {
  skills: string[];
  qualifications: string[];
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
    const [skillsRes, qualificationsRes] = await Promise.all([
      fetch(`${API}/skills`, { headers: getAuthHeaders() }),
      fetch(`${API}/qualifications`, { headers: getAuthHeaders() }),
    ]);

    const [skills, qualifications] = await Promise.all([
      skillsRes.json(),
      qualificationsRes.json(),
    ]);

    cache = {
      skills: skills || [],
      qualifications: qualifications || [],
    };

    return cache;
  })();

  try {
    return await inflight;
  } finally {
    inflight = null;
  }
}

export function prefetchMasters(): void {
  if (cache || inflight) return;
  void fetchMasters();
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
