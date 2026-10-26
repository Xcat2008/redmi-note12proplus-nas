// SPDX-License-Identifier: AGPL-3.0-only
// Redmi NAS integration by José Miranda and contributors.
import yaml from "js-yaml";

const OPTIONAL_JELLYFIN_GPU_DEVICES = new Set([
  "/dev/dri", "/dev/vcsm", "/dev/vchiq", "/dev/video10", "/dev/video11", "/dev/video12",
]);

function hostDevice(entry: unknown): string | undefined {
  if (typeof entry === "string") return entry.split(":")[0];
  if (entry && typeof entry === "object" && "source" in entry) {
    return typeof entry.source === "string" ? entry.source : undefined;
  }
}

function volumeTarget(entry: unknown): string | undefined {
  if (typeof entry === "string") return entry.split(":")[1];
  if (entry && typeof entry === "object" && "target" in entry) {
    return typeof entry.target === "string" ? entry.target : undefined;
  }
}

/** Opt-in software video mode for this port, including fresh catalog installs.
 * Keep unrelated apps and hardware requirements intact. Never add privileges.
 */
export function adaptComposeForHardwareProfile(
  appId: string, source: string, profile: string,
): string {
  if (profile.trim() !== "redmi-ruby-nas" || appId !== "jellyfin") return source;
  const document = yaml.load(source) as { services?: Record<string, Record<string, unknown>> } | null;
  if (!document?.services) return source;
  let changed = false;
  for (const service of Object.values(document.services)) {
    if (!service || typeof service !== "object") continue;
    const image = typeof service.image === "string" ? service.image : "";
    if (!/^(?:lscr\.io\/)?linuxserver\/jellyfin(?::|@|$)/.test(image) &&
        !/^(?:docker\.io\/)?jellyfin\/jellyfin(?::|@|$)/.test(image)) continue;
    if (Array.isArray(service.devices)) {
      const devices = service.devices.filter(entry => !OPTIONAL_JELLYFIN_GPU_DEVICES.has(hostDevice(entry) ?? ""));
      if (devices.length !== service.devices.length) {
        changed = true;
        if (devices.length) service.devices = devices;
        else delete service.devices;
      }
    }
    if (Array.isArray(service.volumes)) {
      const volumes = service.volumes.filter(entry => volumeTarget(entry) !== "/opt/vc/lib");
      if (volumes.length !== service.volumes.length) {
        changed = true;
        service.volumes = volumes;
      }
    }
  }
  return changed ? yaml.dump(document, { lineWidth: -1, noRefs: true }) : source;
}
