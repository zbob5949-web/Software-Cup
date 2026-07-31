from fastapi import APIRouter, HTTPException
from fastapi.responses import HTMLResponse
from pathlib import Path

from app.routers.admin import dashboard, digital_human, faqs, knowledge, reports, bridge, users, conversations, content, orders, consumption

router = APIRouter()

router.include_router(faqs.router)
router.include_router(knowledge.router)
router.include_router(digital_human.router)
router.include_router(dashboard.router)
router.include_router(reports.router)
router.include_router(bridge.router)
router.include_router(users.router)
router.include_router(conversations.router)
router.include_router(content.router)
router.include_router(orders.router)
router.include_router(consumption.router)


ADMIN_HTML = r"""<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>灵山导览 · 管理后台</title>
<style>
:root{font-family:"Microsoft YaHei",Arial,sans-serif;color:#eaf4ef;background:#101715;--panel:#18221f;--line:#30413b;--muted:#9bb0a8;--accent:#68c8a9;--danger:#e27e91}
*{box-sizing:border-box}body{margin:0;background:#101715;display:flex;align-items:center;justify-content:center;min-height:100vh}
.login-box{background:var(--panel);border:1px solid var(--line);border-radius:12px;padding:40px;width:400px;max-width:90vw}
.login-box h1{font-size:24px;margin:0 0 4px;text-align:center}
.login-box .sub{color:var(--muted);text-align:center;margin:0 0 28px;font-size:14px}
.field{margin-bottom:16px}.field label{display:block;font-size:13px;color:var(--muted);margin-bottom:6px}
.field input{width:100%;padding:12px;border:1px solid var(--line);background:#111b18;color:#eaf4ef;border-radius:7px;font-size:15px}
.field input:focus{outline:none;border-color:var(--accent)}
button{width:100%;padding:12px;border:0;border-radius:7px;font-size:16px;font-weight:700;cursor:pointer;background:var(--accent);color:#102019}
button:hover{opacity:.9}button:disabled{opacity:.5;cursor:default}
.msg{margin-top:14px;text-align:center;font-size:14px;min-height:20px}
.msg.err{color:var(--danger)}.msg.ok{color:var(--accent)}
</style>
</head>
<body>
<div class="login-box">
  <h1>灵山导览管理后台</h1>
  <p class="sub">管理员登录</p>
  <div class="field"><label>手机号</label><input id="phone" type="text" placeholder="输入手机号"></div>
  <div class="field"><label>密码</label><input id="password" type="password" placeholder="输入密码" onkeydown="if(event.key==='Enter')login()"></div>
  <button id="btn" onclick="login()">登 录</button>
  <div id="msg" class="msg"></div>
</div>

<script>
var TOKEN='';
var TK='lingshanAdminToken';

function msg(t,c){var e=document.getElementById('msg');e.textContent=t;e.className='msg '+(c||'')}

// Check if already logged in
(function(){
  var saved=localStorage.getItem(TK);
  if(saved){
    TOKEN=saved;
    verifyAndEnter();
  }
})();

async function verifyAndEnter(){
  try{
    var r=await fetch('/api/admin/knowledge/config',{headers:{'Authorization':'Bearer '+TOKEN}});
    var j=await r.json();
    if(j.code===200){enterDashboard()}
    else{localStorage.removeItem(TK);TOKEN=''}
  }catch(e){}
}

async function login(){
  var phone=document.getElementById('phone').value.trim();
  var pw=document.getElementById('password').value.trim();
  if(!phone||!pw){msg('请输入手机号和密码','err');return}
  var btn=document.getElementById('btn');
  btn.disabled=true;btn.textContent='登录中...';msg('','');
  try{
    var r=await fetch('/api/user/login',{
      method:'POST',
      headers:{'Content-Type':'application/json'},
      body:JSON.stringify({phone:phone,password:pw,code:''})
    });
    var j=await r.json();
    if(j.code===200){
      TOKEN=j.data.token;
      localStorage.setItem(TK,TOKEN);
      msg('登录成功，正在跳转...','ok');
      setTimeout(enterDashboard,500);
    }else{
      msg(j.msg||'登录失败','err');
    }
  }catch(e){msg('网络错误: '+e.message,'err')}
  btn.disabled=false;btn.textContent='登 录';
}

function enterDashboard(){
  window.location.href='/admin/knowledge';
}
</script>
</body>
</html>"""


PANEL_HTML = r"""<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>灵山导览 · 管理后台</title>
<style>
:root{font-family:"Microsoft YaHei",Arial,sans-serif;color:#eaf4ef;background:#101715;--panel:#18221f;--line:#30413b;--muted:#9bb0a8;--accent:#68c8a9;--danger:#e27e91}
*{box-sizing:border-box}body{margin:0;background:#101715}
button,input,textarea,select{font:inherit;padding:9px 13px;border-radius:7px}
button{border:1px solid var(--line);background:#22312c;color:var(--accent);cursor:pointer}
button:hover{border-color:var(--accent)}
button.primary{background:var(--accent);color:#102019;border-color:var(--accent);font-weight:700}
button.danger{color:#ff9caf}
input,textarea,select{width:100%;border:1px solid var(--line);background:#111b18;color:#eaf4ef;padding:10px}
textarea{min-height:100px;resize:vertical}
.shell{max-width:1400px;margin:auto;padding:24px}
.topbar{display:flex;justify-content:space-between;align-items:center;margin-bottom:20px}
.topbar h1{font-size:22px;margin:0}.topbar button{width:auto}
.tabs{display:flex;gap:8px;border-bottom:1px solid var(--line);margin-bottom:18px}
.tab{border:0;border-radius:7px 7px 0 0;background:transparent;color:var(--muted);padding:10px 18px;font-size:14px;cursor:pointer}
.tab.active{background:#22312c;color:var(--accent)}
.view{display:none}.view.active{display:block}
.panel{background:var(--panel);border:1px solid var(--line);border-radius:10px;padding:18px;margin-bottom:18px}
.panel h3{margin:0 0 6px;font-size:17px}
.panel .hint{color:var(--muted);font-size:13px;margin:0 0 12px}
.muted{color:var(--muted);font-size:13px}
.status{padding:8px 12px;border:1px solid var(--line);border-radius:7px;color:var(--muted);font-size:13px;margin:10px 0}
.status.ok{color:var(--accent)}
.toolbar{display:flex;gap:8px;align-items:center;flex-wrap:wrap;margin:10px 0}
.toolbar .input{max-width:260px}
table{width:100%;border-collapse:collapse}
th,td{text-align:left;padding:8px 10px;border-bottom:1px solid var(--line)}
th{font-size:12px;color:var(--muted);font-weight:500}td{font-size:13px}
.doc-row{cursor:pointer}.doc-row:hover{background:#1e2a26}.doc-row.sel{background:#1a3028;outline:1px solid var(--accent);outline-offset:-1px}
.doc-name small{display:block;color:var(--muted);font-size:11px;word-break:break-all}
.tag{padding:2px 7px;border-radius:4px;font-size:11px;border:1px solid var(--line)}.tag.ok{color:var(--accent);border-color:#2d5c44}
.actions{display:flex;gap:6px}
.edit-panel{background:#111b18;padding:14px;border-radius:8px;margin-top:10px}
.form-grid{display:grid;grid-template-columns:1fr 1fr;gap:12px}.field{display:grid;gap:6px}.field.full{grid-column:1/-1}
.field label{font-size:13px;color:var(--muted)}
.human-grid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:14px}
.human-card{border:2px solid var(--line);border-radius:10px;padding:14px;background:#141e1b;cursor:pointer;position:relative}
.human-card:hover{border-color:#3d5a4a}.human-card.sel,.human-card.active{border-color:var(--accent)}
.human-card .badge{position:absolute;top:10px;right:10px;background:var(--accent);color:#102019;padding:2px 8px;border-radius:4px;font-size:11px;font-weight:700}
.human-card h3{margin:0 0 4px;font-size:15px}.human-card .meta{font-size:12px;color:var(--muted)}
.human-card.ghost{border-style:dashed;display:flex;align-items:center;justify-content:center;min-height:110px}
.empty{padding:30px;text-align:center;color:var(--muted)}
.toast{position:fixed;top:20px;right:20px;z-index:9999;padding:10px 18px;border-radius:8px;font-size:14px}
.toast.ok{background:#1a3a2a;border:1px solid var(--accent);color:var(--accent)}.toast.err{background:#3a1a22;border:1px solid var(--danger);color:var(--danger)}
@media(max-width:900px){.human-grid{grid-template-columns:1fr 1fr}}
@media(max-width:580px){.shell{padding:14px}.form-grid{grid-template-columns:1fr}.human-grid{grid-template-columns:1fr}}
</style>
</head>
<body>
<div class="shell">
<div class="topbar"><h1>灵山导览管理后台</h1><button onclick="logout()" class="danger">退出登录</button></div>

<nav class="tabs">
  <button class="tab active" data-view="knowledge">知识库管理</button>
  <button class="tab" data-view="human">数字人配置</button>
</nav>

<section id="knowledge" class="view active">
  <div class="panel">
    <h3>Dify 知识库文档</h3>
    <div id="difyStatus" class="status">加载中...</div>
    <div class="toolbar"><input class="input" id="docSearch" placeholder="搜索文档..."><button id="refreshDocs">刷新</button></div>
    <table><thead><tr><th style="width:45%">文档名称</th><th>状态</th><th style="width:18%">时间</th><th style="width:15%">操作</th></tr></thead><tbody id="docRows"><tr><td class="empty" colspan="4">加载中...</td></tr></tbody></table>
    <div id="docEdit" class="edit-panel" style="display:none">
      <div class="form-grid"><div class="field full"><label>文档名称</label><input class="input" id="editName"></div><div class="field full"><label>正文</label><textarea id="editText" style="min-height:180px"></textarea></div></div>
      <div class="toolbar"><button id="saveDoc" class="primary">保存</button><button id="cancelEdit">取消</button></div>
    </div>
  </div>
  <div class="panel">
    <h3>新建文档</h3>
    <div class="field" style="margin-bottom:8px"><label>名称</label><input class="input" id="docName" placeholder="例：灵山大佛讲解词"></div>
    <div class="field" style="margin-bottom:8px"><label>内容</label><textarea id="docText" placeholder="粘贴讲解词..."></textarea></div>
    <div class="toolbar"><button id="createText" class="primary">提交文本</button><input class="input" id="docFile" type="file" style="max-width:160px"><button id="uploadFile">上传文件</button></div>
    <hr style="border-color:var(--line);margin:14px 0"><h3>检索测试</h3>
    <div class="toolbar"><input class="input" id="retrieveQuery" placeholder="输入问题..." style="max-width:100%"><button id="retrieve" class="primary">搜索</button></div>
    <pre id="retrieveResult" class="muted" style="white-space:pre-wrap;max-height:180px;overflow:auto;font-size:12px"></pre>
  </div>
</section>

<section id="human" class="view">
  <div class="panel"><h3>数字人形象</h3><p class="hint">点击卡片编辑，激活后游客端刷新即切换</p><div id="humanRows" class="human-grid"><div class="empty">加载中...</div></div></div>
  <div id="humanEditor" class="panel" style="display:none"><h3 id="humanEditorTitle">编辑</h3>
    <div class="form-grid"><div class="field"><label>模型</label><select class="input" id="humanModel"></select></div><div class="field"><label>名称</label><input class="input" id="humanName"></div><div class="field"><label>声音</label><input class="input" id="humanVoice" placeholder="zh-CN-XiaoyiNeural"></div><div class="field"><label>风格</label><input class="input" id="humanVoiceStyle"></div><div class="field full"><label>关键词</label><input class="input" id="humanKeywords"></div><div class="field full"><label>外观</label><textarea id="humanAppearance" style="min-height:50px"></textarea></div><div class="field"><label>服装</label><textarea id="humanClothing" style="min-height:50px"></textarea></div><div class="field"><label>文化风格</label><textarea id="humanCulture" style="min-height:50px"></textarea></div></div>
    <div class="toolbar"><button id="saveHuman" class="primary">保存</button><button id="activateHuman">保存并激活</button><button id="cancelHumanBtn">取消</button></div>
  </div>
</section>
</div>

<script>
var TOKEN=localStorage.getItem('lingshanAdminToken')||'';
var TK='lingshanAdminToken';
var docs=[],humans=[],catalog=[],editingDoc=null,editingHumanId=null;

function $(id){return document.getElementById(id)}
function esc(s){return String(s||'').replace(/[&<>]/g,function(c){return{'"':'&quot;','&':'&amp;','<':'&lt;','>':'&gt;'}[c]})}
function fmtDate(v){if(!v)return'-';if(typeof v==='number')v=new Date(v*1000).toISOString();return String(v).substring(0,10)}
function toast(t,c){var e=document.createElement('div');e.className='toast '+(c||'ok');e.textContent=t;document.body.appendChild(e);setTimeout(function(){e.remove()},2500)}

async function api(path,opt){
  opt=opt||{};var h=new Headers(opt.headers||{});h.set('Authorization','Bearer '+TOKEN);
  var r=await fetch(path,{headers:h,method:opt.method||'GET',body:opt.body});
  var t=await r.text();var j={};try{j=JSON.parse(t)}catch(e){}
  if(r.status===401){logout();throw new Error('登录已过期，请重新登录')}
  if(!r.ok||(j.code&&j.code!==200))throw new Error(j.detail||j.msg||'HTTP '+r.status);
  return j.data||j
}

function logout(){localStorage.removeItem(TK);window.location.href='/admin'}

// ===== 知识库 =====
async function loadDocs(){
  try{
    var c=await api('/api/admin/knowledge/config');
    $('difyStatus').textContent='数据集: '+c.dataset_id_masked+' | API Key: '+(c.api_key_configured?'已配置':'未配置');
    $('difyStatus').className='status ok';
    var d=await api('/api/admin/knowledge/documents?limit=100');
    docs=d.data||d.documents||d.items||[];renderDocs();
  }catch(e){$('difyStatus').textContent=e.message;$('difyStatus').className='status';$('docRows').innerHTML='<tr><td class="empty" colspan="4">加载失败: '+esc(e.message)+'</td></tr>'}
}

function renderDocs(){
  var q=($('docSearch').value||'').toLowerCase();
  var list=docs.filter(function(d){return!q||(d.name||d.document_name||'').toLowerCase().indexOf(q)!==-1});
  if(!list.length){$('docRows').innerHTML='<tr><td class="empty" colspan="4">暂无文档</td></tr>';return}
  var h='';
  for(var i=0;i<list.length;i++){
    var d=list[i],id=d.id||d.document_id,n=d.name||d.document_name||id,s=d.indexing_status||d.status||'';
    h+='<tr class="doc-row'+(editingDoc===id?' sel':'')+'" data-id="'+esc(id)+'">';
    h+='<td><span class="doc-name">'+esc(n)+'<small>'+esc(id)+'</small></span></td>';
    h+='<td><span class="tag'+(s==='completed'?' ok':'')+'">'+esc(s||'已提交')+'</span></td><td>'+fmtDate(d.updated_at||d.created_at)+'</td>';
    h+='<td class="actions"><button data-edit="'+esc(id)+'">编辑</button><button class="danger" data-del="'+esc(id)+'" data-dname="'+esc(n)+'">删除</button></td></tr>';
  }
  $('docRows').innerHTML=h;
  var rows=$('docRows').querySelectorAll('.doc-row');
  for(var j=0;j<rows.length;j++){rows[j].onclick=function(){startEditDoc(this.getAttribute('data-id'))}}
  var edits=$('docRows').querySelectorAll('[data-edit]');
  for(var k=0;k<edits.length;k++){edits[k].onclick=function(e){e.stopPropagation();startEditDoc(this.getAttribute('data-edit'))}}
  var dels=$('docRows').querySelectorAll('[data-del]');
  for(var m=0;m<dels.length;m++){dels[m].onclick=function(e){e.stopPropagation();delDoc(this.getAttribute('data-del'),this.getAttribute('data-dname'))}}
}

async function startEditDoc(id){
  if(editingDoc===id){cancelEditDoc();return}
  editingDoc=id;renderDocs();
  $('editName').value='加载中...';$('editText').value='加载中...';$('docEdit').style.display='block';
  try{var d=await api('/api/admin/knowledge/documents/'+encodeURIComponent(id));var x=d.data||d;$('editName').value=x.name||x.document_name||'';$('editText').value=x.text||x.content||'';$('docEdit').scrollIntoView({behavior:'smooth'})}catch(e){toast(e.message,'err')}
}
function cancelEditDoc(){editingDoc=null;$('docEdit').style.display='none';renderDocs()}
async function delDoc(id,n){
  if(!confirm('删除「'+n+'」？'))return;
  try{await api('/api/admin/knowledge/documents/'+encodeURIComponent(id),{method:'DELETE'});toast('已删除');if(editingDoc===id)cancelEditDoc();await loadDocs()}catch(e){toast(e.message,'err')}
}

$('cancelEdit').onclick=cancelEditDoc;
$('saveDoc').onclick=async function(){
  if(!editingDoc)return;
  try{await api('/api/admin/knowledge/documents/'+encodeURIComponent(editingDoc)+'/text',{method:'PUT',headers:{'Content-Type':'application/json'},body:JSON.stringify({name:$('editName').value.trim(),text:$('editText').value,process_rule_mode:'automatic'})});toast('保存成功');cancelEditDoc();await loadDocs()}catch(e){toast(e.message,'err')}
};
$('createText').onclick=async function(){
  var n=$('docName').value.trim();if(!n){toast('请输入文档名称','err');return}
  try{await api('/api/admin/knowledge/documents/text',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({name:n,text:$('docText').value,indexing_technique:'high_quality',process_rule_mode:'automatic'})});toast('已提交');$('docName').value='';$('docText').value='';await loadDocs()}catch(e){toast(e.message,'err')}
};
$('uploadFile').onclick=async function(){
  var f=$('docFile').files[0];if(!f){toast('请选择文件','err');return}
  var fd=new FormData();fd.append('file',f);
  try{await api('/api/admin/knowledge/documents/file',{method:'POST',body:fd});toast('已提交');$('docFile').value='';await loadDocs()}catch(e){toast(e.message,'err')}
};
$('retrieve').onclick=async function(){
  try{var r=await api('/api/admin/knowledge/retrieve',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({query:$('retrieveQuery').value,top_k:5})});$('retrieveResult').textContent=JSON.stringify(r,null,2)}catch(e){$('retrieveResult').textContent='错误: '+e.message}
};
$('docSearch').oninput=renderDocs;$('refreshDocs').onclick=loadDocs;

// ===== 数字人 =====
async function loadHumans(){
  try{catalog=(await api('/api/digital-human/catalog')).items||[];humans=(await api('/api/admin/digital-humans')).items||[];$('humanModel').innerHTML=catalog.map(function(x){return'<option value="'+esc(x.model_key)+'">'+esc(x.model_label)+'</option>'}).join('');renderHumans()}catch(e){$('humanRows').innerHTML='<div class="empty">加载失败: '+esc(e.message)+'</div>'}
}
function renderHumans(){
  if(!humans.length){$('humanRows').innerHTML='<div class="empty">暂无配置</div>';return}
  var h='';
  for(var i=0;i<humans.length;i++){
    var x=humans[i];
    h+='<article class="human-card'+(x.is_active?' active':'')+(editingHumanId===x.id?' sel':'')+'" data-hid="'+x.id+'">';
    if(x.is_active)h+='<span class="badge">激活</span>';
    h+='<h3>'+esc(x.name)+'</h3><div class="meta">'+esc(x.model_label||x.model_key)+' &middot; '+esc(x.voice_name||'')+'</div>';
    h+='</article>';
  }
  h+='<article class="human-card ghost" id="newCard"><span style="font-size:24px;color:var(--muted)">+</span></article>';
  $('humanRows').innerHTML=h;
  var cards=$('humanRows').querySelectorAll('.human-card:not(.ghost)');
  for(var j=0;j<cards.length;j++){cards[j].onclick=function(){selectHuman(parseInt(this.getAttribute('data-hid')))}}
  $('newCard').onclick=newHuman;
}
function selectHuman(id){
  editingHumanId=id;var x=humans.find(function(v){return v.id===id});if(!x)return;
  $('humanEditor').style.display='block';$('humanEditorTitle').textContent='编辑 - '+x.name;
  $('humanModel').value=x.model_key;$('humanName').value=x.name||'';$('humanVoice').value=x.voice_name||'';$('humanVoiceStyle').value=x.voice_style||'';
  $('humanKeywords').value=x.keywords||'';$('humanAppearance').value=x.appearance||'';$('humanClothing').value=x.clothing||'';$('humanCulture').value=x.cultural_style||'';
  $('humanEditor').scrollIntoView({behavior:'smooth'});renderHumans();
}
function newHuman(){
  editingHumanId=null;$('humanEditor').style.display='block';$('humanEditorTitle').textContent='新建形象';
  $('humanModel').value=catalog.length?catalog[0].model_key:'';$('humanName').value='';$('humanVoice').value='zh-CN-XiaoyiNeural';
  $('humanVoiceStyle').value='';$('humanKeywords').value='';$('humanAppearance').value='';$('humanClothing').value='';$('humanCulture').value='';
  $('humanEditor').scrollIntoView({behavior:'smooth'});renderHumans();
}
$('cancelHumanBtn').onclick=function(){$('humanEditor').style.display='none';editingHumanId=null;renderHumans()};
$('saveHuman').onclick=function(){saveHuman(false)};$('activateHuman').onclick=function(){saveHuman(true)};
async function saveHuman(active){
  var b={model_key:$('humanModel').value,name:$('humanName').value.trim(),voice_name:$('humanVoice').value.trim(),voice_style:$('humanVoiceStyle').value.trim(),keywords:$('humanKeywords').value.trim(),appearance:$('humanAppearance').value.trim(),clothing:$('humanClothing').value.trim(),cultural_style:$('humanCulture').value.trim(),is_active:active};
  try{
    if(editingHumanId){await api('/api/admin/digital-humans/'+editingHumanId,{method:'PUT',headers:{'Content-Type':'application/json'},body:JSON.stringify(b)});toast('保存成功')}
    else{var r=await api('/api/admin/digital-humans',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(b)});toast('创建成功');editingHumanId=r.id}
    await loadHumans();if(editingHumanId)selectHuman(editingHumanId);
  }catch(e){toast(e.message,'err')}
}

// ===== 标签页 =====
document.querySelectorAll('.tab').forEach(function(b){b.onclick=function(){document.querySelectorAll('.tab').forEach(function(x){x.classList.remove('active')});document.querySelectorAll('.view').forEach(function(x){x.classList.remove('active')});b.classList.add('active');document.getElementById(b.getAttribute('data-view')).classList.add('active')}});

// ===== 加载 =====
loadDocs();loadHumans();
</script>
</body>
</html>"""


@router.get("/legacy-admin", include_in_schema=False)
def admin_page():
    return HTMLResponse(ADMIN_HTML)


@router.get("/legacy-admin/panel", include_in_schema=False)
def admin_panel():
    return HTMLResponse(PANEL_HTML)
