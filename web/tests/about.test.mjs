import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import test from 'node:test';

const webRoot = new URL('../', import.meta.url);
const html = await readFile(new URL('about_sweety.html', webRoot), 'utf8');

test('about page presents Sweety as an open-source project with a safe GitHub link', () => {
  assert.match(html, /<h2>開源專案<\/h2>/);
  assert.match(html, /Sweety 作為主動式反詐 App，完全開源/);
  assert.match(html, /href="https:\/\/github\.com\/ericchen1972\/Sweety"[^>]+target="_blank"[^>]+rel="noopener noreferrer"/);
});

test('about page includes the complete author card below its project content', () => {
  assert.match(html, /class="author-card"/);
  assert.match(html, /src="https:\/\/sweety\.tw\/images\/eric\.png"[^>]+width="256"[^>]+height="256"/);
  for (const text of ['Eric / 網站 / AI 工程師', '20 年開發經驗', 'eric.chen1972@gmail.com', 'bobo2010', '任何程式開發、電商都歡迎與作者接洽']) assert.match(html, new RegExp(text.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')));
  assert.match(html, /<!--email_off-->[\s\S]*eric\.chen1972@gmail\.com[\s\S]*<!--\/email_off-->/);
  for (const href of ['https://slimweb.tw', 'https://slimweb.tw/kingjoo/', 'https://sweety.tw']) {
    assert.match(html, new RegExp(`href="${href.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')}"[^>]+target="_blank"[^>]+rel="noopener noreferrer"`));
  }
});

test('about page has canonical and social metadata', () => {
  assert.match(html, /<link rel="canonical" href="https:\/\/sweety\.tw\/about_sweety\.html">/);
  assert.match(html, /<meta name="description" content="[^"]+">/);
  assert.match(html, /<meta property="og:image" content="https:\/\/sweety\.tw\/images\/sweety-social-1200x630\.png">/);
});
