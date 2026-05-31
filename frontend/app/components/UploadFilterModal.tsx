"use client";

import { useState, useEffect, useMemo } from "react";

type Props = {
  files: FileList;
  skills: string[];
  qualifications: string[];
  onClose: () => void;
  onSuccess: () => void;
};

export default function UploadFilterModal({
  files,
  skills: initialSkills,
  qualifications: initialQualifications,
  onClose,
  onSuccess,
}: Props) {

  const [selectedSkills, setSelectedSkills] = useState<string[]>([]);
  const [selectedQualifications, setSelectedQualifications] = useState<string[]>([]);

  const [experienceType, setExperienceType] = useState("minimum");

  // ✅ STRING keeps decimals safe (0.7, 1.5 etc)
  const [experienceValue, setExperienceValue] = useState("0.7");

  const [loading, setLoading] = useState(false);

  // memo prevents rerender lag
  const skills = useMemo(() => initialSkills || [], [initialSkills]);
  const qualifications = useMemo(() => initialQualifications || [], [initialQualifications]);

  useEffect(() => {
    if (!files) return;

    setSelectedSkills([]);
    setSelectedQualifications([]);
    setExperienceType("minimum");
    setExperienceValue("0.7");
  }, [files]);

  const toggleSkill = (skill: string) => {
    setSelectedSkills(prev =>
      prev.includes(skill)
        ? prev.filter(s => s !== skill)
        : [...prev, skill]
    );
  };

  const toggleQualification = (q: string) => {
    setSelectedQualifications(prev =>
      prev.includes(q)
        ? prev.filter(x => x !== q)
        : [...prev, q]
    );
  };

  const handleUpload = async () => {
    setLoading(true);

    const formData = new FormData();

    Array.from(files).forEach(file => {
      formData.append("files", file);
    });

    formData.append("skills", JSON.stringify(selectedSkills));
    formData.append("qualifications", JSON.stringify(selectedQualifications));
    formData.append("experience_type", experienceType);

    // ✅ FIX: preserves 0.7, 1.5
    formData.append("experience_value", experienceValue);

    try {
      const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/upload/cvs`, {
        method: "POST",
        body: formData,
      });

      const data = await res.json();

      if (data.success) {
        onSuccess();
        onClose();
      } else {
        alert(data.message || "Upload failed");
      }

    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50">

      <div className="bg-white w-full max-w-3xl rounded-3xl p-6 max-h-[90vh] overflow-y-auto">

        <h2 className="text-2xl font-bold mb-6">CV Filter Setup</h2>

        {/* EXPERIENCE */}
        <div className="mb-6">
          <h3 className="font-semibold mb-3">Experience</h3>

          <select
            value={experienceType}
            onChange={(e) => setExperienceType(e.target.value)}
            className="border px-3 py-2 rounded-xl w-full mb-3"
          >
            <option value="minimum">Minimum</option>
            <option value="more_than">More Than</option>
            <option value="exact">Exact</option>
          </select>

          <input
            type="number"
            step="0.1"
            min="0"
            value={experienceValue}
            onChange={(e) => setExperienceValue(e.target.value)}
            className="border px-3 py-2 rounded-xl w-full"
          />
        </div>

        {/* SKILLS */}
        <div className="mb-6">
          <h3 className="font-semibold mb-3">Skills</h3>

          <div className="grid grid-cols-2 gap-2">
            {skills.map(skill => (
              <label key={skill} className="flex items-center gap-2">
                <input
                  type="checkbox"
                  checked={selectedSkills.includes(skill)}
                  onChange={() => toggleSkill(skill)}
                />
                {skill}
              </label>
            ))}
          </div>
        </div>

        {/* QUALIFICATIONS */}
        <div className="mb-6">
          <h3 className="font-semibold mb-3">Qualifications</h3>

          <div className="grid grid-cols-2 gap-2">
            {qualifications.map(q => (
              <label key={q} className="flex items-center gap-2">
                <input
                  type="checkbox"
                  checked={selectedQualifications.includes(q)}
                  onChange={() => toggleQualification(q)}
                />
                {q}
              </label>
            ))}
          </div>
        </div>

        {/* ACTIONS */}
        <div className="flex justify-end gap-3">
          <button onClick={onClose} className="px-4 py-2 border rounded-xl">
            Cancel
          </button>

          <button
            onClick={handleUpload}
            disabled={loading}
            className="px-5 py-2 bg-cyan-600 text-white rounded-xl"
          >
            {loading ? "Uploading..." : "Filter & Upload"}
          </button>
        </div>

      </div>
    </div>
  );
}