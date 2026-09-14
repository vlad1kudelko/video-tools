// fetch() has no upload-progress event, so the upload phase of a big file/zip
// looks frozen. XMLHttpRequest does expose one (xhr.upload.onprogress) —
// wrapped here behind a fetch-like {ok, status, json()} result so call sites
// barely change.
export function uploadWithProgress(url, formData, onProgress) {
  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest();
    xhr.open("POST", url);
    xhr.upload.onprogress = e => {
      if (e.lengthComputable && onProgress) onProgress(e.loaded / e.total);
    };
    xhr.onload = () => resolve({
      ok: xhr.status >= 200 && xhr.status < 300,
      status: xhr.status,
      json: () => Promise.resolve(xhr.responseText ? JSON.parse(xhr.responseText) : {}),
    });
    xhr.onerror = () => reject(new Error("network error"));
    xhr.send(formData);
  });
}

// Upload and processing are two phases of one overall progress bar, not two
// separate bars — without this the bar would jump back to 0% the moment the
// upload finishes and server-side processing starts.
export const UPLOAD_WEIGHT = 0.3;
export function combinedPct(uploadFrac, processFrac, uploadWeight = UPLOAD_WEIGHT) {
  return Math.round((uploadFrac * uploadWeight + processFrac * (1 - uploadWeight)) * 100);
}
