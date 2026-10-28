let cached: boolean | undefined;

/** Whether this browser can create a WebGL context. Some VMs, remote desktops and locked-down
 *  browsers cannot, and three.js then throws while mounting. Checked once, on the client; the
 *  probe context is released right away so it does not count against the page's limit. */
export function hasWebGL(): boolean {
  if (cached !== undefined) return cached;
  if (typeof window === "undefined") return true;
  try {
    const canvas = document.createElement("canvas");
    const gl = (canvas.getContext("webgl2") || canvas.getContext("webgl")) as WebGLRenderingContext | null;
    cached = Boolean(gl);
    gl?.getExtension("WEBGL_lose_context")?.loseContext();
  } catch {
    cached = false;
  }
  return cached;
}
