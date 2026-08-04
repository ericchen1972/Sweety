# Japanese Tutorial Video Localization Design

## Goal

Create a Japanese edition of the existing long-form Sweety tutorial while preserving the current picture edit. Replace the narration and subtitles with natural Japanese. Do not rerecord the App or redesign the video.

## Source and Deliverables

- Use the existing Traditional Chinese tutorial as the picture source, preferring an original local master when available and otherwise using the best available published copy.
- Reuse the existing 149-cue subtitle timeline as the timing source.
- Produce an editable `ja-JP.srt` file with the same cue identifiers, timestamps, and intentionally blank cues.
- Produce a synchronized Japanese female voiceover as a 48 kHz mono MP3.
- Produce an MP4 that keeps the original video frames, uses the Japanese narration, and includes burned-in Japanese subtitles.
- Copy final user-facing media to `/Volumes/1TB/Codex-Media/videos`; place the editable SRT and standalone voiceover beside the video or in the corresponding audio directory.

## Translation and Voice Direction

- Translate for natural spoken Japanese rather than following Chinese word order literally.
- Keep product names such as Sweety, LINE, OpenAI, macOS, and Windows recognizable and consistent.
- Preserve the instructional meaning and safety constraints, especially that Sweety replies only to selected targets and only after an unread message arrives.
- Use a calm, friendly, adult Japanese female voice suitable for a software tutorial.
- Shorten individual lines where needed so speech fits the original cue window without sounding rushed.

## Audio and Subtitle Processing

- Generate narration cue by cue so each spoken segment can be fitted to its subtitle window.
- Prefer rewriting an overlong Japanese line before applying speed adjustment.
- Preserve useful interface sounds where possible. If the available source contains mixed Chinese narration, attenuate or separate that speech before mixing Japanese narration; do not leave competing narration audible.
- Burn Japanese subtitles into the final MP4 for immediate viewing and also retain the sidecar SRT for YouTube or later editing.

## Verification

- Confirm all 149 cues are present and cue timestamps remain ordered.
- Confirm blank cues remain blank and no spoken segment exceeds its assigned window.
- Confirm the final audio reaches the expected 578.833-second endpoint without trimmed tail silence.
- Confirm the MP4 has the original picture duration, a valid Japanese audio track, readable subtitles, and no audible Chinese narration competing with the Japanese voice.
- Review representative sections from the beginning, middle, and end for translation quality, pronunciation, subtitle wrapping, and synchronization.

## Publishing Boundary

This task delivers verified local media files. Uploading the Japanese video to YouTube and changing the public homepage video ID are separate publishing actions and require explicit approval after the completed MP4 is reviewed.

## Out of Scope

- Re-recording the App with a Japanese interface.
- Changing the existing Chinese or English tutorial videos.
- Translating the App, homepage copy, or base personas in this video-production step.
