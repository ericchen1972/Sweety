# macOS 12 Compatibility Assessment

Assessment date: 2026-07-27

## Current release

The published macOS bundle cannot run on macOS 12.

- `app/desktop/Sweety.spec` sets `LSMinimumSystemVersion` to `13.0`, so Finder rejects the app before launch.
- `app/desktop/dist/Sweety.app/Contents/MacOS/Sweety` is arm64-only. It cannot run on an Intel Mac regardless of macOS version.
- A Mach-O audit of the current app found:
  - 85 bundled binaries targeting macOS 11;
  - 75 targeting macOS 13, primarily the current OpenCV package and its libraries;
  - 15 targeting macOS 14, from the current NumPy and ONNX Runtime packages.
- The resolved OCR stack currently includes `opencv-python==5.0.0.93`, `numpy==2.4.6`, and `onnxruntime==1.27.0`.

Changing only `LSMinimumSystemVersion` to `12.0` would remove the Finder warning but would leave incompatible native libraries. The app would fail when those libraries load.

## Feasibility

Supporting macOS 12 is feasible, but it requires a compatibility build and testing rather than a plist-only change.

### Recommended: use native Vision OCR

The macOS app only needs OCR for unread contact names. Chat content now goes directly to the multimodal AI as a screenshot. Replacing RapidOCR with the macOS Vision text-recognition framework would allow the macOS bundle to remove RapidOCR, OpenCV, ONNX Runtime, and their NumPy dependency.

This is the smallest long-term dependency surface for a macOS-only adapter and should also reduce the app and DMG size.

### Alternative: pin an older OCR stack

PyPI currently provides potentially compatible wheels including:

- `opencv-python==4.10.0.84`: Apple Silicon wheel tagged for macOS 11 and Intel wheel tagged for macOS 12;
- `onnxruntime==1.19.2`: CPython 3.11 universal2 wheel tagged for macOS 11.

This path requires pinning every native dependency, rebuilding from a clean environment, and auditing the resulting Mach-O `minos` values. Wheel filenames alone are not sufficient proof of runtime compatibility.

## Required release validation

Before lowering the declared minimum:

1. Build an Apple Silicon artifact whose every bundled Mach-O file targets macOS 12 or earlier.
2. Build a separate Intel artifact or a verified universal2 artifact.
3. Install and launch on actual macOS 12 hardware for each supported architecture.
4. Verify Screen Recording, Accessibility, and Automation permission prompts.
5. Verify LINE window discovery, unread-name OCR, screenshot capture, AI response, paste, Enter, window close, and permission recovery after an update.
6. Set `LSMinimumSystemVersion` to `12.0` only after the complete artifact passes.

The current release target remains macOS 13 until this matrix succeeds.
