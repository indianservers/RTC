import ninada from "ninada";
import * as ort from "onnxruntime-web/wasm";
import wasmUrl from "onnxruntime-web/ort-wasm-simd-threaded.wasm?url";
import wasmModuleUrl from "onnxruntime-web/ort-wasm-simd-threaded.mjs?url";

// Bundle the matching runtime assets; models load only when Telugu is spoken.
ort.env.wasm.numThreads = 1;
ort.env.wasm.wasmPaths = { wasm: wasmUrl, mjs: wasmModuleUrl };

export async function createTeluguVoice() {
  let session: Promise<ort.InferenceSession> | undefined;
  const voice = await ninada({
    lang: "te",
    voice: "female",
    ort,
    getSession: () => {
      session ??= (async () => {
        const url = "/voices/te_female.onnx";
        const cache =
          "caches" in window
            ? await caches.open("rtc-ninada-25143ee2").catch(() => undefined)
            : undefined;
        let response = await cache?.match(url);
        if (!response) {
          response = await fetch(url, { signal: AbortSignal.timeout(60000) });
          if (!response.ok) throw new Error("Telugu voice download failed");
          await cache?.put(url, response.clone()).catch(() => {});
        }
        return ort.InferenceSession.create(await response.arrayBuffer(), {
          executionProviders: ["wasm"],
        });
      })().catch((error) => {
        session = undefined;
        throw error;
      });
      return session;
    },
  });
  const dispose = voice.dispose.bind(voice);
  voice.dispose = async () => {
    await dispose();
    await session?.then((loaded) => loaded.release()).catch(() => {});
  };
  return voice;
}
