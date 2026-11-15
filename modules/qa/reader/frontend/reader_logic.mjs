export function normalizeText(value) {
  return String(value ?? "").normalize("NFC").replace(/\s+/g, " ").trim().toLocaleLowerCase();
}

export function normalizeRect(rect, pageBounds, page) {
  if (!pageBounds?.width || !pageBounds?.height) throw new Error("page bounds must have positive dimensions");
  const clamp = value => Math.max(0, Math.min(1, value));
  const left = clamp((rect.left - pageBounds.left) / pageBounds.width);
  const top = clamp((rect.top - pageBounds.top) / pageBounds.height);
  const right = clamp((rect.right - pageBounds.left) / pageBounds.width);
  const bottom = clamp((rect.bottom - pageBounds.top) / pageBounds.height);
  return {page, x:left, y:top, w:Math.max(0,right-left), h:Math.max(0,bottom-top)};
}

export function selectionStartPage(rects, fallback = 1) {
  const page = rects?.[0]?.page;
  return Number.isInteger(page) && page > 0 ? page : fallback;
}

export function findTextInSpans(spans, needle) {
  const text = spans.join(" ");
  const start = normalizeText(text).indexOf(normalizeText(needle));
  return start < 0 ? null : {start, end:start + normalizeText(needle).length};
}

export function newEventId(cryptoObject = globalThis.crypto) {
  return cryptoObject?.randomUUID?.() || `${Date.now()}-${Math.random().toString(16).slice(2)}`;
}
