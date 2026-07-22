# Persona Catalog Refresh Design

## Goal

Replace the distorted 35-50 persona artwork, prevent raw style JSON from appearing in the UI, and add a complete 50-65 remote persona group for update testing.

## Root Causes

The six 35-50 files were produced by slicing a 3-by-2 contact sheet whose cells were not 16:9, then resizing each slice to 1280-by-720. The files report a 16:9 size but the subjects inside them are horizontally distorted.

The API returns `speech_style_zh_tw` and `speech_style_en` as display strings. Those database fields currently contain serialized JSON, so the detail modal renders that JSON verbatim.

## Catalog Content

The 35-50 group keeps its current six persona identities but receives independently generated artwork and natural-language style descriptions.

The 50-65 group contains three women and three men:

- Careful community pharmacist
- Busy market stall owner
- Retired school administrator
- Practical hardware store owner
- Apartment building manager
- Semi-retired logistics dispatcher

Each persona has localized name, summary, profile, style, AI text, and one independent illustration.

## Artwork

Each of the twelve new illustrations is generated independently as a natural, editorial-style Taiwanese workplace portrait. The generated source is center-cropped to 16:9 and resized to 1280-by-720 without stretching. No contact sheets, text, logos, or watermarks are used.

## Compatibility

Remote style fields are changed from JSON to prose for every existing persona. The frontend also detects a legacy JSON style string and converts it to a short readable description, covering the interval before a successful remote refresh.

The persona detail modal presents profile and style as one continuous persona-content section. Their storage fields remain separate only for backward compatibility and are not presented as a required semantic distinction.

The custom-persona modal labels its name field `人設名稱`, uses `ex. 猶豫不決的小會計` as the name placeholder, and uses `請在這裡輸入人物的基本資訊，姓名、年齡、工作、個性、說話風格等` as the persona text placeholder.

The server endpoint includes `20-35`, `35-50`, and `50-65`. Deployment verification requires six active personas per age group, balanced three women and three men, readable non-JSON style fields, and the expected total of eighteen personas.

## Refresh And Verification

After remote deployment succeeds, the local SQLite rows for `35-50` are deleted, including their embedded image data. Sweety is relaunched so remote synchronization repopulates 35-50 and adds 50-65. Verification checks remote and local counts, image dimensions, non-JSON style text, frontend tests, desktop tests, the rebuilt app, and the live local API.

## About Sweety

The sidebar adds `關於 Sweety` immediately after Persona Editor. The local backend fetches `https://sweety.tw/about_sweety.html`, removes scripts, styles, forms, embedded frames, event handlers, and unsafe links, then returns a safe HTML fragment to the frontend. The frontend renders that fragment in the normal document flow so its height follows the content naturally. A local loading state, failure message, and retry action remain available when the remote page cannot load.
