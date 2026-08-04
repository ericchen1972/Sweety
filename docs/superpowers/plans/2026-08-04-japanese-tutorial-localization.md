# Japanese Tutorial Localization Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Deliver a Japanese-narrated, Japanese-captioned edition of the existing 1080p Sweety tutorial without changing its picture edit.

**Architecture:** Treat the published Traditional Chinese tutorial as an immutable picture master. Compile a reviewed Japanese translation against the existing 149-cue timeline, synthesize and time-fit each voiced cue, replace the source audio, burn a normalized Japanese subtitle track, and retain standalone subtitle and voiceover artifacts.

**Tech Stack:** Node.js 24, HeyGen Starfish TTS, FFmpeg/FFprobe, yt-dlp, SRT, JSON

---

### Task 1: Freeze and validate source media

**Files:**
- Read: `/Users/eric/tmp_img/Subtitle 1.srt`
- Create: `/Users/eric/tmp_img/sweety_japanese_tutorial_work/source/Sweety-Chinese-Tutorial.mkv`
- Create: `/Users/eric/tmp_img/sweety_japanese_tutorial_work/source/source-probe.json`

- [ ] **Step 1: Download the public 1080p picture source**

```bash
uvx yt-dlp --js-runtimes node:/Users/eric/.nvm/versions/node/v24.15.0/bin/node \
  -f 'bv*[height<=1080]+ba/b[height<=1080]' \
  --merge-output-format mkv \
  -o '/Users/eric/tmp_img/sweety_japanese_tutorial_work/source/Sweety-Chinese-Tutorial.%(ext)s' \
  'https://www.youtube.com/watch?v=w2w5HGmXxwo'
```

- [ ] **Step 2: Probe source streams and duration**

```bash
ffprobe -v error -show_format -show_streams -of json \
  '/Users/eric/tmp_img/sweety_japanese_tutorial_work/source/Sweety-Chinese-Tutorial.mkv' \
  > '/Users/eric/tmp_img/sweety_japanese_tutorial_work/source/source-probe.json'
```

Expected: 1920×1080 picture, approximately 582 seconds, and at least one audio stream.

- [ ] **Step 3: Verify the subtitle source contract**

Parse the SRT and assert exactly 149 cues, ordered identifiers, 14 blank cues, and an endpoint of `01:09:38,833`.

### Task 2: Produce and validate the Japanese subtitle master

**Files:**
- Create: `/Users/eric/tmp_img/sweety_japanese_tutorial_work/translations.ja-JP.json`
- Create: `/Users/eric/tmp_img/sweety_japanese_tutorial_work/Subtitle 1.ja-JP.source-timecode.srt`
- Create: `/Users/eric/tmp_img/sweety_japanese_tutorial_work/Sweety-Tutorial.ja-JP.srt`
- Create: `/Users/eric/tmp_img/sweety_japanese_tutorial_work/build_and_verify_subtitles.mjs`

- [ ] **Step 1: Translate all nonblank cues into natural spoken Japanese**

Preserve cue meaning and product terminology. Keep blank cue values as empty strings and shorten Japanese wording where the original cue window is tight.

- [ ] **Step 2: Build both source-timecode and normalized SRT files**

The source-timecode file retains the original one-hour editing offset. The normalized file subtracts 3600 seconds so it can be burned into or uploaded with the final video.

- [ ] **Step 3: Run subtitle contract checks**

```bash
/Users/eric/.nvm/versions/node/v24.15.0/bin/node \
  /Users/eric/tmp_img/sweety_japanese_tutorial_work/build_and_verify_subtitles.mjs
```

Expected: `PASS`, 149 cues, 135 voiced cues, 14 blank cues, and matching relative timestamps. Review the Japanese text manually for untranslated Chinese prose because Japanese legitimately contains CJK ideographs.

### Task 3: Select and synthesize the Japanese female voice

**Files:**
- Create: `/Users/eric/tmp_img/sweety_japanese_tutorial_work/voice-sample.mp3`
- Create: `/Users/eric/tmp_img/sweety_japanese_tutorial_work/synthesize_and_mix.mjs`
- Create: `/Users/eric/tmp_img/sweety_japanese_tutorial_work/segments/*.mp3`
- Create: `/Users/eric/tmp_img/sweety_japanese_tutorial_work/segments/*.wav`
- Create: `/Users/eric/tmp_img/sweety_japanese_tutorial_work/Sweety-Tutorial.ja-JP.voiceover.mp3`
- Create: `/Users/eric/tmp_img/sweety_japanese_tutorial_work/timing-report.json`

- [ ] **Step 1: Generate a Japanese voice sample using the existing Starfish female voice**

```bash
/Users/eric/.nvm/versions/node/v24.15.0/bin/node \
  /Users/eric/.agents/skills/media-use/audio/scripts/heygen-tts.mjs \
  'こんにちは、エリックです。今日は、私が開発した詐欺対策アプリ「Sweety」をご紹介します。' \
  --lang ja --voice 05f19352e8f74b0392a8f411eba40de1 \
  -o /Users/eric/tmp_img/sweety_japanese_tutorial_work/voice-sample.mp3
```

Expected: valid Japanese pronunciation from a calm adult female voice.

- [ ] **Step 2: Synthesize each of the 135 voiced cues**

Use `--lang ja` and the same voice ID for every cue. Cache raw segment files so the process can resume safely.

- [ ] **Step 3: Fit speech to each cue window and mix the timeline**

Use FFmpeg `atempo`, mono resampling, short fades, `adelay`, `amix`, and tail padding. Rewrite translations when a cue would require a speed ratio above `1.25`.

- [ ] **Step 4: Verify the voiceover**

Expected: 135 voiced cues, no cue overflow, maximum speed ratio no greater than `1.25`, 48 kHz mono MP3, and duration `578.833 ± 0.03` seconds.

### Task 4: Assemble and inspect the final MP4

**Files:**
- Create: `/Users/eric/tmp_img/sweety_japanese_tutorial_work/Sweety-Tutorial-ja-JP.mp4`
- Create: `/Users/eric/tmp_img/sweety_japanese_tutorial_work/final-probe.json`

- [ ] **Step 1: Replace the source audio and burn Japanese subtitles**

```bash
ffmpeg -y \
  -i '/Users/eric/tmp_img/sweety_japanese_tutorial_work/source/Sweety-Chinese-Tutorial.mkv' \
  -i '/Users/eric/tmp_img/sweety_japanese_tutorial_work/Sweety-Tutorial.ja-JP.voiceover.mp3' \
  -map 0:v:0 -map 1:a:0 \
  -vf "subtitles='/Users/eric/tmp_img/sweety_japanese_tutorial_work/Sweety-Tutorial.ja-JP.srt':force_style='FontName=Hiragino Sans,FontSize=22,Outline=2,Shadow=0,MarginV=42'" \
  -c:v libx264 -preset slow -crf 18 -c:a aac -b:a 192k \
  -metadata:s:a:0 language=jpn -movflags +faststart \
  '/Users/eric/tmp_img/sweety_japanese_tutorial_work/Sweety-Tutorial-ja-JP.mp4'
```

- [ ] **Step 2: Probe and visually inspect representative frames**

Check the beginning, middle, and end for Japanese subtitle wrapping, safe margins, picture continuity, audio synchronization, and absence of audible Chinese narration.

- [ ] **Step 3: Run final media checks**

Expected: non-empty H.264/AAC MP4, 1920×1080, the same duration as the source picture (approximately 582 seconds), Japanese audio metadata, and readable burned-in subtitles. The standalone narration may end at 578.833 seconds while the final picture continues through its original closing frames.

### Task 5: Deliver final artifacts on the 1TB volume

**Files:**
- Create: `/Volumes/1TB/Codex-Media/videos/Sweety-Tutorial-ja-JP.mp4`
- Create: `/Volumes/1TB/Codex-Media/videos/Sweety-Tutorial-ja-JP.srt`
- Create: `/Volumes/1TB/Codex-Media/audio/Sweety-Tutorial-ja-JP.voiceover.mp3`

- [ ] **Step 1: Copy verified files to final storage**

Use explicit source and destination paths and preserve the working files under `/Users/eric/tmp_img`.

- [ ] **Step 2: Verify delivered checksums and probes**

```bash
shasum -a 256 \
  '/Volumes/1TB/Codex-Media/videos/Sweety-Tutorial-ja-JP.mp4' \
  '/Volumes/1TB/Codex-Media/videos/Sweety-Tutorial-ja-JP.srt' \
  '/Volumes/1TB/Codex-Media/audio/Sweety-Tutorial-ja-JP.voiceover.mp3'
ffprobe -v error -show_format -show_streams -of json \
  '/Volumes/1TB/Codex-Media/videos/Sweety-Tutorial-ja-JP.mp4'
```

Expected: all three files exist, are non-empty, and match their verified working copies.
