// 検証用の 3 ページ。widget のページは token かエラーを widget 側のオリジンの /report に送る
export type PageName = "Y_direct" | "X_iframe_Y" | "X_direct";

export function widgetPage(params: { sitekey: string; page: PageName; reportUrl: string; instruction: string }): string {
  const { sitekey, page, reportUrl, instruction } = params;
  return `<!doctype html><html><head><meta charset="utf-8">
<script src="https://challenges.cloudflare.com/turnstile/v0/api.js?render=explicit" async defer onload="go()"></script></head>
<body style="font-family:sans-serif;margin:8px">${instruction ? `<p style="font-size:18px">${instruction}</p>` : ""}
<div id="w"></div><p id="s">状態: 読み込み中</p><script>
window.__result = null;
function send(r){
  window.__result = r;
  document.getElementById('s').textContent = '状態: ' + (r.token ? 'token を受け取りました' : 'エラー ' + r.error);
  const ancestors = location.ancestorOrigins ? Array.from(location.ancestorOrigins) : null;
  fetch(${JSON.stringify(reportUrl)}, {method:'POST', headers:{'content-type':'application/json'},
    body: JSON.stringify({page:${JSON.stringify(page)}, ...r, ua:navigator.userAgent, location:location.href,
      referrer:document.referrer, ancestorOrigins:ancestors})}).catch(() => {});
}
function go(){ turnstile.render('#w',{sitekey:${JSON.stringify(sitekey)},
  callback:(t)=>send({token:t}),
  'error-callback':(c)=>{send({error:String(c)}); return true;},
  'unsupported-callback':()=>send({error:'unsupported'}),
  'timeout-callback':()=>send({error:'timeout'})}); }
</script></body></html>`;
}

export function embedPage(params: { widgetOrigin: string }): string {
  return `<!doctype html><html><head><meta charset="utf-8"></head><body style="font-family:sans-serif">
<h1>設置先 X</h1>
<p style="font-size:18px">手順 2: 下の枠の中のチェックボックスを押してください (自動で済んだときは押さなくてよい)。</p>
<iframe src="${params.widgetOrigin}/widget.html" width="420" height="160" style="border:1px solid #888"></iframe></body></html>`;
}
