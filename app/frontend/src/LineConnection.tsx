import type {Copy} from "./i18n";
import {useEffect,useState} from "react";
import {api} from "./api";
import type {Locale} from "./domain";

export interface LineContact {id:string;name:string;alias?:string;originalName?:string;avatarUrl?:string;blocked:boolean;targetId?:string|null;kind?:"person"|"group"}
export interface LineStatus {status:string;name?:string;qr?:string;pin?:string;error?:string;streamError?:string;avatarUrl?:string}
export const lineCopy={
 "zh-TW":{title:"LINE 連線",login:"登入 LINE",logout:"登出 LINE",hint:"按登入後，用手機 LINE 掃描 QR Code 並確認登入。",pin:"請在手機輸入驗證碼",cancel:"取消登入",connecting:"正在連線…",expired:"QR Code 已過期，請重新登入。",search:"搜尋聯絡人或群組",refresh:"重新整理",empty:"沒有符合的對象",choose:"選取 LINE 對象",blocked:"已封鎖／無法加入",added:"已加入",group:"群組（名稱／標註觸發回覆）",unbound:"待綁定 LINE 聯絡人",unavailable:"目前帳號無法監控",bind:"綁定 LINE 對象",bindHint:"選取實際的 LINE 對象以綁定舊資料。原本人設、武器、對話與統計會保留。",needLogin:"請先登入 LINE，再選取對象。",stop:"請先停止監控，再變更 LINE 設定。",none:"選擇對象",connected:"已登入",connectionLost:"無法連到 Sweety，請確認 App 正在執行。恢復連線後會自動更新。"},
 en:{title:"LINE connection",login:"Log in to LINE",logout:"Log out of LINE",hint:"Click Log in, then scan and approve the QR code with LINE on your phone.",pin:"Enter this code on your phone",cancel:"Cancel login",connecting:"Connecting…",expired:"QR code expired. Log in again.",search:"Search people or groups",refresh:"Refresh",empty:"No matching contacts",choose:"Choose a LINE contact",blocked:"Blocked / unavailable",added:"Already added",group:"Group (name / mention replies)",unbound:"LINE binding required",unavailable:"Unavailable for this account",bind:"Bind LINE contact",bindHint:"Choose the actual contact to bind existing data. Personas, weapons, messages and statistics are preserved.",needLogin:"Log in to LINE to choose contacts.",stop:"Stop monitoring before changing LINE settings.",none:"Choose contact",connected:"Connected",connectionLost:"Cannot reach Sweety. Make sure the app is running; this view will update when it reconnects."},
 ja:{title:"LINE接続",login:"LINEにログイン",logout:"LINEからログアウト",hint:"ログインを押し、スマートフォンのLINEでQRコードを読み取って承認してください。",pin:"スマートフォンに確認コードを入力",cancel:"ログインを取消",connecting:"接続中…",expired:"QRコードの期限切れです。再ログインしてください。",search:"連絡先・グループを検索",refresh:"更新",empty:"該当する対象がありません",choose:"LINEの対象を選択",blocked:"ブロック中／利用不可",added:"追加済み",group:"グループ（名前・メンション返信）",unbound:"LINE連携が必要",unavailable:"現在のアカウントでは利用不可",bind:"LINEの対象を連携",bindHint:"実際の対象を選択してください。既存のキャラクター・武器・会話・統計は保持されます。",needLogin:"LINEにログインして対象を選択してください。",stop:"設定変更前に監視を停止してください。",none:"対象を選択",connected:"接続済み",connectionLost:"Sweetyに接続できません。Appを起動してください。接続回復後に自動更新します。"}
};
export function filterContacts(rows:LineContact[],query:string){const q=query.trim().toLowerCase();return rows.filter(t=>[t.name,t.alias,t.originalName].some(n=>n?.toLowerCase().includes(q)));}
export function ContactIdentity({contact}:{contact:LineContact}){
 const [failed,setFailed]=useState(false);
 return <span className="flex min-w-0 items-center gap-3">{contact.avatarUrl && !failed?<img src={contact.avatarUrl} onError={()=>setFailed(true)} alt="" className="h-10 w-10 shrink-0 rounded-full object-cover"/>:<span aria-hidden="true" className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-sky-100 text-sky-800">{Array.from(contact.name)[0] || "?"}</span>}<span className="min-w-0"><strong className="block break-words">{contact.name}</strong><small className="block text-slate-500">{contact.id.slice(-6)}</small></span></span>;
}
export function reloadLineState(){window.dispatchEvent(new Event("sweety:reload"));}
const lineErrorCopy={
 "zh-TW":{session:"LINE 登入已失效，請按「登入 LINE」重新掃碼登入。",restore:"無法恢復先前的 LINE 登入，請確認網路連線後重新登入。",login:"LINE 登入未完成，請確認網路連線與手機上的登入提示，再試一次。",other:"LINE 連線發生問題，請確認網路連線；若仍無法使用，請重新登入 LINE。",details:"查看診斷詳細資料"},
 en:{session:"Your LINE session is no longer valid. Click Log in to LINE and scan the QR code again.",restore:"Could not restore your previous LINE session. Check your connection and log in again.",login:"LINE login did not complete. Check your connection and the prompts on your phone, then try again.",other:"There is a problem connecting to LINE. Check your connection; if it continues, log in to LINE again.",details:"Show diagnostic details"},
 ja:{session:"LINEのログインが無効になりました。「LINEにログイン」を押し、QRコードで再ログインしてください。",restore:"以前のLINEログインを復元できません。ネットワーク接続を確認し、再ログインしてください。",login:"LINEへのログインが完了しませんでした。ネットワーク接続とスマートフォンの案内を確認し、再試行してください。",other:"LINEへの接続に問題が発生しました。ネットワーク接続を確認し、改善しない場合は再ログインしてください。",details:"診断の詳細を表示"}
};
export function LineError({locale,error}:{locale:Locale;error:string}){
 const c=lineErrorCopy[locale];
 const session=/\bV3_TOKEN_CLIENT_LOGGED_OUT\b|\bNOT_AUTHORIZED_DEVICE\b/.test(error);
 const message=session?c.session:error.startsWith("line_restore_failed:")?c.restore:error.startsWith("line_login_failed:")?c.login:c.other;
 return <div className="mt-3 rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-700 dark:border-red-900 dark:bg-red-950 dark:text-red-300"><p role="alert">{message}</p><details className="mt-2"><summary className="cursor-pointer">{c.details}</summary><pre className="mt-2 max-h-64 overflow-auto whitespace-pre-wrap break-words font-mono text-xs [overflow-wrap:anywhere]">{error}</pre></details></div>;
}
export function startLineStatusPolling(load:()=>Promise<LineStatus>,onStatus:(status:LineStatus)=>void,onConnectionError:(failed:boolean)=>void) {
 let active=true;
 const read=async()=>{try{const value=await load();if(active){onConnectionError(false);onStatus(value);}}catch{if(active)onConnectionError(true);}};
 void read();const timer=setInterval(()=>{void read();},1200);
 return ()=>{active=false;clearInterval(timer);};
}
export function LineConnection({locale,locked}:{locale:Locale;locked:boolean}){
 const c=lineCopy[locale];const [line,setLine]=useState<LineStatus>({status:"disconnected"});const [busy,setBusy]=useState(false),[error,setError]=useState(""),[connectionError,setConnectionError]=useState(false);
 useEffect(()=>{let last="";return startLineStatusPolling(()=>api.lineStatus(),value=>{setLine(value);if(last && last!==value.status)reloadLineState();last=value.status;},setConnectionError);},[]);

 async function act(logout=false){setBusy(true);setError("");try{if(logout)await api.lineLogout();else await api.lineLogin();setLine(await api.lineStatus());reloadLineState();}catch(e){setError(e instanceof Error?e.message:String(e));}finally{setBusy(false);}}
 const pending=["connecting","qr","pin"].includes(line.status);
 return <section className="mb-6 rounded-xl border border-zinc-200 bg-white p-5 dark:border-zinc-800 dark:bg-zinc-950"><div className="flex flex-wrap items-center justify-between gap-3"><div><h2 className="text-lg font-semibold">{c.title}</h2>{line.status==="connected"?<p className="mt-1 text-sm text-emerald-600">{c.connected} · {line.name}</p>:<p className="mt-1 text-sm text-slate-500">{c.hint}</p>}</div><button className="secondary-button" disabled={locked || busy} onClick={()=>void act(line.status==="connected" || pending)}>{line.status==="connected"?c.logout:pending?c.cancel:c.login}</button></div>{pending && <p className="mt-3 text-sm" role="status">{c.connecting}</p>}{line.qr && <img className="mt-4 h-56 w-56 max-w-full rounded bg-white p-2" src={line.qr} alt="LINE QR Code"/>}{line.pin && <p className="mt-3">{c.pin}: <strong>{line.pin}</strong></p>}{line.status==="expired" && <p role="status">{c.expired}</p>}{locked && <p className="mt-2 text-sm text-slate-500">{c.stop}</p>}{connectionError && <p className="mt-3 text-sm text-red-600" role="alert">{c.connectionLost}</p>}{(error || line.error || line.streamError) && <LineError locale={locale} error={error || line.error || line.streamError || ""}/>}</section>;
}
export function ContactPicker({locale,value,onChange}:{locale:Locale;value:LineContact|null;onChange:(contact:LineContact)=>void}){
 const c=lineCopy[locale];const [rows,setRows]=useState<LineContact[]>([]),[query,setQuery]=useState(""),[scope,setScope]=useState("people"),[error,setError]=useState(""),[busy,setBusy]=useState(false);
 async function load(refresh=false){setBusy(true);setError("");try{const status=await api.lineStatus();if(status.status!=="connected")throw new Error(c.needLogin);setRows(await api.lineContacts(refresh));}catch(e){setError(e instanceof Error?e.message:String(e));}finally{setBusy(false);}}
 useEffect(()=>{void load();},[]);
 const visible=filterContacts(rows,query).filter(t=>scope==="groups"?t.kind==="group":t.kind!=="group");
 return <div><div className="mb-3 flex gap-2"><button type="button" className={scope==="people"?"primary-button":"secondary-button"} onClick={()=>setScope("people")}>{locale==="zh-TW"?"個人聯絡人":locale==="ja"?"連絡先":"People"}</button><button type="button" className={scope==="groups"?"primary-button":"secondary-button"} onClick={()=>setScope("groups")}>{locale==="zh-TW"?"LINE 群組":locale==="ja"?"LINEグループ":"LINE groups"}</button></div><div className="mb-3 flex gap-2"><input aria-label={c.search} type="search" className="form-input min-w-0 flex-1" placeholder={c.search} value={query} onChange={e=>setQuery(e.target.value)}/><button type="button" className="secondary-button" disabled={busy} onClick={()=>void load(true)}>{c.refresh}</button></div><div className="max-h-56 space-y-2 overflow-y-auto rounded-lg border border-zinc-200 p-2 dark:border-zinc-800">{visible.map(t=><button type="button" key={t.id} aria-pressed={value?.id===t.id} disabled={busy || !!t.blocked || !!t.targetId} onClick={()=>onChange(t)} className={`flex w-full items-center justify-between gap-3 rounded-lg p-3 text-left disabled:opacity-40 ${value?.id===t.id?"bg-sky-100 ring-2 ring-sky-500 dark:bg-sky-950":"hover:bg-slate-100 dark:hover:bg-zinc-900"}`}><ContactIdentity contact={t}/><span className="text-xs">{t.blocked?c.blocked:t.targetId?c.added:t.kind==="group"?c.group:""}</span></button>)}{!visible.length && <p className="p-3 text-sm text-slate-500">{busy?c.connecting:c.empty}</p>}</div>{error && <p role="alert" className="mt-2 text-sm text-red-600">{error}</p>}</div>;
}

export function UserNamesField({value,onChange,copy}:{value:string;onChange:(value:string)=>void;copy:Copy}) {
 return <label className="block"><span className="mb-2 block text-sm font-medium">{copy.userNamesLabel}</span><input type="text" className="form-input" maxLength={500} value={value} onChange={event=>onChange(event.target.value)} placeholder="小美,美姐"/><span className="mt-2 block text-xs leading-5 text-slate-500 dark:text-zinc-400">{copy.userNamesHint}</span></label>;
}
