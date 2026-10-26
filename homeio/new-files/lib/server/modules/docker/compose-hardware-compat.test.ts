import { test } from "node:test";
import assert from "node:assert/strict";
import yaml from "js-yaml";
import { adaptComposeForHardwareProfile as adapt } from "./compose-hardware-compat";

const catalog = `services:
  jellyfin:
    image: linuxserver/jellyfin:12.2ubu2604-ls53
    devices:
      - /dev/dri:/dev/dri
      - /dev/vcsm:/dev/vcsm
      - /dev/vchiq:/dev/vchiq
      - /dev/video10:/dev/video10
      - /dev/video11:/dev/video11
      - /dev/video12:/dev/video12
    volumes:
      - type: bind
        source: /opt/vc/lib
        target: /opt/vc/lib
      - /DATA/Media:/Media:ro
      - /DATA/AppData/jellyfin/config:/config
    ports:
      - '8097:8096'
    restart: unless-stopped
`;

test("fresh catalog Jellyfin removes Raspberry Pi GPU dependencies and preserves data/ports", () => {
  const result = yaml.load(adapt("jellyfin", catalog, "redmi-ruby-nas\n")) as { services: { jellyfin: Record<string, unknown> } };
  const service = result.services.jellyfin;
  assert.equal(service.devices, undefined);
  assert.deepEqual(service.volumes, ["/DATA/Media:/Media:ro", "/DATA/AppData/jellyfin/config:/config"]);
  assert.deepEqual(service.ports, ["8097:8096"]);
  assert.equal(service.restart, "unless-stopped");
  assert.equal(service.privileged, undefined);
});

test("hosts without the explicit Redmi profile retain hardware requirements", () => {
  assert.equal(adapt("jellyfin", catalog, ""), catalog);
  assert.equal(adapt("jellyfin", catalog, "raspberry-pi"), catalog);
});

test("other apps, including the NVIDIA variant, are unchanged", () => {
  assert.equal(adapt("frigate", catalog, "redmi-ruby-nas"), catalog);
  assert.equal(adapt("jellyfin-nvidia", catalog, "redmi-ruby-nas"), catalog);
});

test("unrelated devices, services and volume mounts are preserved", () => {
  const extra = catalog.replace("      - /dev/vcsm:/dev/vcsm", "      - /dev/vcsm:/dev/vcsm\n      - /dev/dvb:/dev/dvb");
  const result = yaml.load(adapt("jellyfin", extra, "redmi-ruby-nas")) as { services: { jellyfin: Record<string, unknown> } };
  assert.deepEqual(result.services.jellyfin.devices, ["/dev/dvb:/dev/dvb"]);
});

test("long device syntax and short Broadcom volume syntax are supported", () => {
  const source = `services:\n  jellyfin:\n    image: jellyfin/jellyfin:10\n    devices:\n      - source: /dev/vchiq\n        target: /dev/vchiq\n    volumes:\n      - /opt/vc/lib:/opt/vc/lib:ro\n      - /media:/media:ro\n`;
  const result = yaml.load(adapt("jellyfin", source, "redmi-ruby-nas")) as { services: { jellyfin: Record<string, unknown> } };
  assert.equal(result.services.jellyfin.devices, undefined);
  assert.deepEqual(result.services.jellyfin.volumes, ["/media:/media:ro"]);
});

test("already adapted compose is stable and unknown images are left unchanged", () => {
  const fixed = adapt("jellyfin", catalog, "redmi-ruby-nas");
  assert.equal(adapt("jellyfin", fixed, "redmi-ruby-nas"), fixed);
  const unknown = catalog.replace("linuxserver/jellyfin:", "example/another-app:");
  assert.equal(adapt("jellyfin", unknown, "redmi-ruby-nas"), unknown);
});
