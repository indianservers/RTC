// Self-host Ninada's Telugu specialist so inference obeys connect-src 'self'.
import { createHash } from "node:crypto";
import { mkdir, readFile, rename, writeFile } from "node:fs/promises";

const target = new URL("../public/voices/te_female.onnx", import.meta.url);
const expected =
  "747c815c31044578b9763f04266ca6874e07639740bc11a3051945be806c01c4";
const digest = (bytes) => createHash("sha256").update(bytes).digest("hex");
let installed = false;
try {
  installed = digest(await readFile(target)) === expected;
} catch {
  /* First install. */
}
if (!installed) {
  console.log(
    "Preparing Ninada Telugu voice (22.7 MB, cached for later builds)...",
  );
  const response = await fetch(
    "https://huggingface.co/gnumanth/ninada/resolve/25143ee2842dd7bd9e2955b94797d43590ca676e/onnx_mobile/te_female.onnx",
    { signal: AbortSignal.timeout(180000) },
  );
  if (!response.ok)
    throw new Error(`Ninada model download failed: ${response.status}`);
  const bytes = new Uint8Array(await response.arrayBuffer());
  if (digest(bytes) !== expected)
    throw new Error("Ninada model checksum mismatch");
  await mkdir(new URL("../public/voices/", import.meta.url), {
    recursive: true,
  });
  const temporary = new URL(`${target.href}.download`);
  await writeFile(temporary, bytes);
  await rename(temporary, target);
}
