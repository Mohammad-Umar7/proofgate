import * as THREE from "three";

/** Muted subsystem hues so highlights (green path, red ghost) carry all the meaning. */
const SUBSYSTEMS: [prefix: string, color: string, label: string][] = [
  ["lib/vtls/", "#8f7cff", "TLS backends"],
  ["lib/vauth/", "#4fd1c5", "Auth"],
  ["lib/vquic/", "#e879c6", "QUIC / HTTP/3"],
  ["lib/vssh/", "#f6ad55", "SSH"],
  ["lib/curlx/", "#94a3b8", "Portability"],
  ["src/", "#9ae6b4", "curl tool"],
  ["lib/", "#7aa2ff", "libcurl core"],
];

export function subsystem(file: string) {
  return SUBSYSTEMS.find(([p]) => file.startsWith(p)) ?? SUBSYSTEMS[SUBSYSTEMS.length - 1];
}

export function nodeColor(file: string): THREE.Color {
  return new THREE.Color(subsystem(file)[1]);
}

export const LEGEND = SUBSYSTEMS.map(([, color, label]) => ({ color, label }));
