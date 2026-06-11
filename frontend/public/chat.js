(function(){
  var API="http://94.74.90.21:8000";
  var open=false, msgs=[];
  var botSvg='<svg width="14" height="14" fill="none" stroke="#fff" stroke-width="2" viewBox="0 0 24 24"><rect width="16" height="12" x="4" y="8" rx="2"/><path d="M2 14h2M20 14h2M12 8V4H8"/></svg>';
  var userSvg='<svg width="14" height="14" fill="none" stroke="#fff" stroke-width="2" viewBox="0 0 24 24"><path d="M19 21v-2a4 4 0 0 0-4-4H9a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/></svg>';

  var btn=document.createElement("button");
  btn.id="chatBtn";
  btn.innerHTML='<svg width="24" height="24" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/></svg>';
  btn.style.cssText="position:fixed;bottom:24px;right:24px;z-index:99999;width:56px;height:56px;border-radius:50%;background:#111827;color:#fff;border:none;cursor:pointer;display:flex;align-items:center;justify-content:center;box-shadow:0 4px 16px rgba(0,0,0,0.2)";
  btn.onclick=function(){showPanel()};
  document.body.appendChild(btn);

  var panel=document.createElement("div");
  panel.id="chatPanel";
  panel.style.cssText="position:fixed;bottom:24px;right:24px;z-index:99999;width:380px;height:520px;background:#fff;border-radius:16px;overflow:hidden;box-shadow:0 12px 40px rgba(0,0,0,0.15);border:1px solid #e2e8f0;display:none;flex-direction:column;font-family:-apple-system,sans-serif";

  var header=document.createElement("div");
  header.style.cssText="background:#111827;padding:14px 20px;display:flex;align-items:center;justify-content:space-between";
  header.innerHTML='<div style="display:flex;align-items:center;gap:10px"><div style="width:32px;height:32px;border-radius:8px;background:rgba(255,255,255,0.1);display:flex;align-items:center;justify-content:center">'+botSvg.replace(/14/g,'16')+'</div><div><div style="color:#fff;font-size:14px;font-weight:600">InsightPro 智能助手</div><div style="color:rgba(255,255,255,0.5);font-size:10px">DeepSeek · 流式回答</div></div></div>';
  var closeBtn=document.createElement("button");
  closeBtn.style.cssText="background:rgba(255,255,255,0.1);border:none;border-radius:6px;width:28px;height:28px;cursor:pointer;display:flex;align-items:center;justify-content:center";
  closeBtn.innerHTML='<svg width="16" height="16" fill="none" stroke="#fff" stroke-width="2" viewBox="0 0 24 24"><path d="M18 6 6 18M6 6l12 12"/></svg>';
  closeBtn.onclick=function(){hidePanel()};
  header.appendChild(closeBtn);
  panel.appendChild(header);

  var msgBox=document.createElement("div");
  msgBox.id="chatMsgs";
  msgBox.style.cssText="flex:1;overflow-y:auto;padding:16px;display:flex;flex-direction:column;gap:12px";

  var welcome=document.createElement("div");
  welcome.style.cssText="display:flex;gap:10px";
  welcome.innerHTML='<div style="width:28px;height:28px;border-radius:8px;background:#111827;display:flex;align-items:center;justify-content:center;flex-shrink:0">'+botSvg+'</div><div style="background:#f8fafc;border-radius:12px 12px 12px 4px;padding:10px 14px;max-width:85%"><p style="margin:0;font-size:13px;color:#374151;line-height:1.6">你好！我是 InsightPro 智能助手，支持流式回答。可以问平台功能、行业数据、友商分析等问题。</p></div>';
  msgBox.appendChild(welcome);

  var quickBox=document.createElement("div");
  quickBox.style.cssText="padding-left:38px;display:flex;flex-direction:column;gap:6px";
  quickBox.innerHTML='<p style="margin:0;font-size:10px;font-weight:600;color:#94a3b8;text-transform:uppercase;letter-spacing:0.05em">快速提问</p>';
  ["平台有哪些核心功能？","友商洞察包含哪些场景？","如何订阅每日邮件？","行业案例库有哪些内容？"].forEach(function(q){
    var b=document.createElement("button");
    b.textContent=q;
    b.style.cssText="display:block;width:100%;text-align:left;font-size:12px;color:#6366f1;background:#eef2ff;border:none;padding:8px 12px;border-radius:8px;cursor:pointer";
    b.onclick=function(){sendMsg(q)};
    quickBox.appendChild(b);
  });
  msgBox.appendChild(quickBox);
  panel.appendChild(msgBox);

  var inputArea=document.createElement("div");
  inputArea.style.cssText="border-top:1px solid #f1f5f9;padding:12px 16px";
  var inputRow=document.createElement("div");
  inputRow.style.cssText="display:flex;gap:8px";
  var input=document.createElement("input");
  input.id="chatInput";
  input.placeholder="输入你的问题...";
  input.style.cssText="flex:1;padding:8px 12px;border-radius:8px;background:#f8fafc;border:1px solid #e2e8f0;font-size:13px;outline:none";
  input.onkeydown=function(e){if(e.key==="Enter"&&!e.shiftKey){e.preventDefault();sendMsg(this.value)}};
  var sendBtn=document.createElement("button");
  sendBtn.style.cssText="width:36px;height:36px;border-radius:8px;background:#111827;color:#fff;border:none;cursor:pointer;display:flex;align-items:center;justify-content:center";
  sendBtn.innerHTML='<svg width="16" height="16" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><path d="m22 2-7 20-4-9-9-4Z"/><path d="M22 2 11 13"/></svg>';
  sendBtn.onclick=function(){sendMsg(input.value)};
  inputRow.appendChild(input);
  inputRow.appendChild(sendBtn);
  inputArea.appendChild(inputRow);
  var hint=document.createElement("p");
  hint.style.cssText="margin:6px 0 0;font-size:9px;color:#94a3b8;text-align:center";
  hint.textContent="DeepSeek-V3 · 流式回答 · 站点知识库";
  inputArea.appendChild(hint);
  panel.appendChild(inputArea);

  document.body.appendChild(panel);

  function showPanel(){open=true;panel.style.display="flex";btn.style.display="none";input.focus()}
  function hidePanel(){open=false;panel.style.display="none";btn.style.display="flex"}

  function addMsg(role,content){
    var isUser=role==="user";
    var d=document.createElement("div");
    d.style.cssText="display:flex;gap:10px;flex-direction:"+(isUser?"row-reverse":"row");
    var avatar='<div style="width:28px;height:28px;border-radius:8px;background:'+(isUser?"#6366f1":"#111827")+';display:flex;align-items:center;justify-content:center;flex-shrink:0">'+(isUser?userSvg:botSvg)+'</div>';
    var bubble='<div class="chat-bubble" style="max-width:85%;padding:10px 14px;border-radius:'+(isUser?"12px 12px 4px 12px":"12px 12px 12px 4px")+';background:'+(isUser?"#6366f1":"#f8fafc")+';color:'+(isUser?"#fff":"#374151")+'"><p style="margin:0;font-size:13px;line-height:1.6;white-space:pre-wrap">'+content.replace(/</g,"&lt;")+'</p></div>';
    d.innerHTML=avatar+bubble;
    msgBox.appendChild(d);
    msgBox.scrollTop=msgBox.scrollHeight;
    return d.querySelector("p");
  }

  function sendMsg(text){
    if(!text.trim())return;
    msgs.push({role:"user",content:text.trim()});
    addMsg("user",text.trim());
    input.value="";
    var replyP=addMsg("assistant","");
    var fullReply="";
    fetch(API+"/api/chat/stream",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({message:text.trim(),history:msgs.slice(-6)})})
    .then(function(response){
      var reader=response.body.getReader();
      var decoder=new TextDecoder();
      function read(){
        return reader.read().then(function(result){
          if(result.done){msgs.push({role:"assistant",content:fullReply});return}
          var chunk=decoder.decode(result.value,{stream:true});
          var lines=chunk.split("\n");
          for(var i=0;i<lines.length;i++){
            var line=lines[i];
            if(line.indexOf("data: ")===0){
              var data=line.slice(6);
              if(data==="[DONE]")continue;
              try{
                var parsed=JSON.parse(data);
                var delta=parsed.choices&&parsed.choices[0]&&parsed.choices[0].delta&&parsed.choices[0].delta.content;
                if(delta){fullReply+=delta;replyP.textContent=fullReply;msgBox.scrollTop=msgBox.scrollHeight}
              }catch(e){}
            }
          }
          return read();
        });
      }
      return read();
    })
    .catch(function(){if(!fullReply)replyP.textContent="网络异常，请检查后端服务"});
  }
})();
