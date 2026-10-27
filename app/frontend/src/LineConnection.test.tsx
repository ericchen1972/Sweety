import {getCopy} from "./i18n";
import {describe,it,expect,vi} from "vitest";
import {renderToStaticMarkup} from "react-dom/server";
import {filterContacts,ContactIdentity,LineConnection,LineError,UserNamesField,startLineStatusPolling} from "./LineConnection";

it("explains a revoked LINE session and keeps the traceback collapsed",()=>{
 const error='line_restore_failed: Traceback\nLineAuthError: V3_TOKEN_CLIENT_LOGGED_OUT code=8';
 const html=renderToStaticMarkup(<LineError locale="zh-TW" error={error}/>);
 expect(html).toContain('LINE 登入已失效，請按「登入 LINE」重新掃碼登入。');
 expect(html).toContain('<details');expect(html).not.toMatch(/<details[^>]*\bopen\b/);
 expect(html).toContain('查看診斷詳細資料');expect(html).toContain('V3_TOKEN_CLIENT_LOGGED_OUT');
 expect(html.match(/role="alert">([^<]+)/)?.[1]).not.toContain('Traceback');
});

it("does not mistake every restore failure for invalid credentials",()=>{
 const html=renderToStaticMarkup(<LineError locale="zh-TW" error="line_restore_failed: network timeout"/>);
 expect(html).toContain('請確認網路連線後重新登入');expect(html).not.toContain('登入已失效');
 for(const locale of ['en','ja'] as const){
  const localized=renderToStaticMarkup(<LineError locale={locale} error="line_login_failed: TLS failure"/>);
  expect(localized).not.toContain('LINE 登入未完成');expect(localized).toContain('TLS failure');
 }
});

describe("LINE directory",()=>{
 it("searches aliases and keeps equal names as separate identities",()=>{
  const rows=[{id:"u1",name:"同名",originalName:"原名",blocked:false},{id:"u2",name:"同名",blocked:false}];
  expect(filterContacts(rows,"同名")).toHaveLength(2);
  expect(filterContacts(rows,"原名")[0].id).toBe("u1");
 });
 it("shows avatar and identity suffix for same-name selection",()=>{
  const html=renderToStaticMarkup(<ContactIdentity contact={{id:"u12345678",name:"中文 😊",blocked:false,avatarUrl:"https://profile.line-scdn.net/test"}}/>);
  expect(html).toContain("中文 😊");expect(html).toContain("345678");expect(html).toContain("<img");
 });
 it("has an explicit login entry without permission or category steps",()=>{
  const html=renderToStaticMarkup(<LineConnection locale="zh-TW" locked={false}/>);
  expect(html).toContain("登入 LINE");expect(html).not.toContain("分類");expect(html).not.toContain("BlackHole");
 });
});

 it("offers names and nicknames for group reply triggers",()=>{
  const html=renderToStaticMarkup(<UserNamesField value="小美,美姐" onChange={()=>{}} copy={getCopy("zh-TW")}/>);
  expect(html).toContain("用戶名稱（選填）");expect(html).toContain("小美,美姐");expect(html).toContain("標註");
 });

it("recovers the LINE connection indicator after a temporary local API outage",async()=>{
 vi.useFakeTimers();
 const load=vi.fn().mockRejectedValueOnce(new TypeError("Failed to fetch")).mockResolvedValue({status:"disconnected"});
 const statuses:unknown[]=[],errors:boolean[]=[];
 const stop=startLineStatusPolling(load,status=>statuses.push(status),failed=>errors.push(failed));
 await vi.advanceTimersByTimeAsync(0);
 expect(errors).toEqual([true]);
 await vi.advanceTimersByTimeAsync(1200);
 expect(errors).toEqual([true,false]);expect(statuses).toEqual([{status:"disconnected"}]);
 stop();await vi.advanceTimersByTimeAsync(5000);expect(load).toHaveBeenCalledTimes(2);
 vi.useRealTimers();
});
