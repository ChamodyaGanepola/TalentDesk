const API = process.env.NEXT_PUBLIC_API_URL;

const headers = {
  "ngrok-skip-browser-warning": "true",
};

type MastersData = {
  skills: string[];
  qualifications: string[];
};

let cache: MastersData | null = null;
let inflight: Promise<MastersData> | null = null;

export function getCachedMasters(): MastersData | null {
  return cache;
}

export async function fetchMasters(force = false): Promise<MastersData> {
  if (!force && cache) return cache;
  if (!force && inflight) return inflight;

  inflight = (async () => {
    const [skillsRes, qualificationsRes] = await Promise.all([
      fetch(`${API}/skills`, { headers }),
      fetch(`${API}/qualifications`, { headers }),
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
