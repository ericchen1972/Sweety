import {describe, expect, it} from 'vitest';
import {renderToStaticMarkup} from 'react-dom/server';
import {CodexOption, CodexSettings} from './CodexSettings';
import {getCopy} from './i18n';

const copy = getCopy('zh-TW');

describe('Codex settings', () => {
  it('only offers detected Codex, retaining an unavailable saved selection', () => {
    expect(renderToStaticMarkup(<CodexOption status={null} selected={false} copy={copy}/>)).toBe('');
    expect(renderToStaticMarkup(<CodexOption status={{available:true,ready:false,status:'codex_login_required'}} selected={false} copy={copy}/>)).toContain('value="codex"');
    expect(renderToStaticMarkup(<CodexOption status={{available:false,ready:false,status:'codex_not_installed'}} selected={true} copy={copy}/>)).toContain('disabled');
  });
  it('offers login without asking for an API key', () => {
    const html = renderToStaticMarkup(<CodexSettings status={{available:true,ready:false,status:'codex_login_required'}} copy={copy} refresh={async()=>{}}/>);
    expect(html).toContain('登入 ChatGPT');
    expect(html).not.toContain('type="password"');
    expect(html).toContain('尚未登入');
  });
  it('offers a connection test for a signed in account', () => {
    const html = renderToStaticMarkup(<CodexSettings status={{available:true,ready:true,status:'codex_ready'}} copy={copy} refresh={async()=>{}}/>);
    expect(html).toContain('測試連線');
    expect(html).toContain('已登入');
  });
});
