import { authFetch, getAuthHeaders } from "@/app/lib/auth";
import { getApiBase, readApiErrorMessage } from "@/app/lib/api";

export async function downloadExcelForBatch(batchId: string): Promise<string> {
  const api = getApiBase();
  if (!api) {
    throw new Error("API URL is not configured.");
  }

  let res = await authFetch(`/resume/export/${batchId}/file`);

  if (!res || res.status === 404) {
    const regen = await authFetch(`/resume/export/${batchId}/regenerate`, {
      method: "POST",
    });
    if (!regen) {
      throw new Error("Cannot reach the server.");
    }
    if (!regen.ok) {
      const regenErr = await regen.json().catch(() => ({}));
      throw new Error(
        readApiErrorMessage(regenErr, "Excel could not be regenerated.")
      );
    }
    const regenData = await regen.json();
    const excelPath = String(regenData?.excel_file || "").replace(/\\/g, "/");
    if (!excelPath) {
      throw new Error("Excel file path missing from server.");
    }
    const fileUrl = excelPath.startsWith("http")
      ? excelPath
      : `${api}/${excelPath.replace(/^\/+/, "")}`;
    res = await fetch(fileUrl, { headers: getAuthHeaders() });
  }

  if (!res) {
    throw new Error("Cannot reach the server.");
  }

  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(
      readApiErrorMessage(err, "Excel could not be downloaded. Please try again.")
    );
  }

  const disposition = res.headers.get("Content-Disposition") || "";
  const match = disposition.match(/filename=\"?([^\";]+)\"?/i);
  const fileName =
    match?.[1] || `shortlisted-${batchId.slice(0, 8)}.xlsx`;

  const blob = await res.blob();
  const url = window.URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = fileName;
  document.body.appendChild(a);
  a.click();
  a.remove();
  window.URL.revokeObjectURL(url);

  return fileName;
}
