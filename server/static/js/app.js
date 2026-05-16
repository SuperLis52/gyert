let T={feed:'Лента',messages:'Сообщения',notifications:'Уведомления',profile:'Профиль',search:'Поиск',settings:'Настройки',logout:'Выйти',follow:'Подписаться',unfollow:'Отписаться',send:'Отправить',reply:'Ответить',edit:'Редактировать',delete:'Удалить',save:'Сохранить',online:'в сети',typing:'печатает',today:'Сегодня',yesterday:'Вчера',no_posts:'Нет постов',no_chats:'Нет сообщений',write_post:'Что нового?',create_post:'Опубликовать',followers:'подписчиков',following:'подписок',posts:'постов',edit_profile:'Редактировать',copied:'Скопировано!',deleted:'Удалено',edited:'ред.',nft_code:'Код NFT',activate:'Активировать'};
function t(k){return T[k]||k}

function toggleUserMenu(){document.getElementById('userMenu').classList.toggle('open')}

class App{
    constructor(){
        this.me=null;this.socket=null;this.page=document.body.dataset.page||'feed';
        this.chatId=null;this.chats=[];this.typingTm=null;this.replyTo=null;this.feedPage=1;
        this.contactNames=JSON.parse(localStorage.getItem('gyert_cn')||'{}');
        this.init();
    }

    async init(){
        try{const r=await fetch('/api/me');if(!r.ok)throw 0;this.me=await r.json()}catch(e){location.href='/login';return}
        this.applyTheme(this.me.theme||'light');
        this.socket=io();
        this.setupSocket();
        this.updateNav();
        if(this.me.email && !this.me.email_verified){const b=document.getElementById('verifyBanner');if(b)b.style.display='flex'}
        this.renderSidebar();
        await this.loadPage();
        this.loadRecommended();
        this.updateBadges();
        setInterval(()=>this.updateBadges(),15000);
        document.addEventListener('click',e=>{
            const um=document.getElementById('userMenu');if(um&&!um.contains(e.target)&&!document.getElementById('navAvatarWrap').contains(e.target))um.classList.remove('open');
            const ctx=document.getElementById('ctxMenu');if(ctx)ctx.style.display='none';
        });
        this.setupSearch();
        document.querySelectorAll('.th-btn').forEach(b=>b.onclick=()=>{
            document.querySelectorAll('.th-btn').forEach(x=>x.classList.remove('active'));
            b.classList.add('active');this.applyTheme(b.dataset.theme);
            fetch('/api/settings',{method:'PUT',headers:{'Content-Type':'application/json'},body:JSON.stringify({theme:b.dataset.theme})});
        });
        // Mobile nav highlight
        document.querySelectorAll('.mn-btn').forEach(b=>{const p=new URL(b.href).pathname.split('/')[1]||'feed';b.classList.toggle('active',this.page===p)});
    }

    // ══════ LOAD PAGE ══════
    async loadPage(){
        const c=document.getElementById('pageContent');if(!c)return;
        const sb=document.getElementById('storiesBar');const sr=document.getElementById('sidebarRight');
        if(this.page==='feed'){
            if(sb)sb.style.display='';if(sr)sr.style.display='';
            c.innerHTML=this.cpBox()+'<div id="feedList"></div>';this.setupCP();await this.loadFeed();this.loadStories();
        }else if(this.page==='messages'){
            if(sb)sb.style.display='none';if(sr)sr.style.display='none';
            c.innerHTML=this.msgLayout();await this.loadChats();
            const p=new URLSearchParams(location.search);if(p.get('chat'))setTimeout(()=>this.openChat(+p.get('chat')),300);
        }else if(this.page==='notifications'){
            if(sb)sb.style.display='none';if(sr)sr.style.display='';
            c.innerHTML='<div id="notifList"></div>';await this.loadNotifs();
        }else if(this.page==='profile'){
            if(sb)sb.style.display='none';if(sr)sr.style.display='';
            await this.renderProfile(document.body.dataset.target||this.me.username);
        }else if(this.page==='search'){
            if(sb)sb.style.display='none';if(sr)sr.style.display='';
            c.innerHTML='<div class="search-page"><input type="text" placeholder="Поиск..." id="spInp"><div id="spRes"></div></div>';
            document.getElementById('spInp').oninput=e=>this.searchP(e.target.value);document.getElementById('spInp').focus();
        }else if(this.page==='reels'){
            if(sb)sb.style.display='none';if(sr)sr.style.display='none';
            c.innerHTML='<div id="reelsC" class="reels-container"></div>';await this.loadReels();
        }else if(this.page==='ai'){
            if(sb)sb.style.display='none';if(sr)sr.style.display='none';
            c.innerHTML=this.aiPage();
        }else if(this.page==='premium'){
            if(sb)sb.style.display='none';if(sr)sr.style.display='none';
            c.innerHTML='<div id="premiumPage"></div>';await this.loadPremium();
        }else if(this.page==='music'){
            if(sb)sb.style.display='none';if(sr)sr.style.display='none';
            c.innerHTML='<div class="empty-state"><div class="es-icon">🎵</div><h3>Gyert Music</h3><p>Скоро!</p></div>';
        }else if(this.page==='post'){
            if(sb)sb.style.display='none';if(sr)sr.style.display='';
            const pid=document.body.dataset.postId;if(pid)await this.renderPostPage(+pid);
        }
    }

    // ══════ SOCKET ══════
    setupSocket(){
        this.socket.on('new_message',d=>this.onMsg(d));
        this.socket.on('message_edited',d=>{const el=document.querySelector('[data-msg="'+d.id+'"] .mtxt');if(el)el.textContent=d.content});
        this.socket.on('message_deleted',d=>{const el=document.querySelector('[data-msg="'+d.message_id+'"] .mtxt');if(el){el.textContent=t('deleted');el.style.opacity='.5'}});
        this.socket.on('messages_read',d=>{if(d.chat_id===this.chatId)d.message_ids.forEach(mid=>{const el=document.querySelector('[data-msg="'+mid+'"] .chk');if(el){el.className='chk read';el.textContent='✓✓'}})});
        this.socket.on('user_typing',d=>{if(d.chat_id===this.chatId){let ti=document.getElementById('typInd');if(!ti){ti=document.createElement('div');ti.id='typInd';ti.className='typing-ind';document.getElementById('mList')?.appendChild(ti)}ti.innerHTML=this.esc(d.display_name)+' '+t('typing')+' <span></span><span></span><span></span>'}});
        this.socket.on('user_stop_typing',d=>{if(d.chat_id===this.chatId)document.getElementById('typInd')?.remove()});
        this.socket.on('user_status',d=>{const st=document.getElementById('cvpSt');if(st&&this.chatId){const ch=this.chats.find(c=>c.id===this.chatId);if(ch?.other_user?.id===d.user_id){st.className='cvp-status '+(d.is_online?'online':'');st.textContent=d.is_online?t('online'):this.fmtL(d.last_seen)}}});
        this.socket.on('notification',d=>{this.toast('🔔 '+(d.text||''));this.updateBadges()});
        this.socket.on('chat_created',()=>{if(this.page==='messages')this.loadChats()});
        this.socket.on('reaction_updated',d=>{if(d.chat_id!==this.chatId)return;const el=document.querySelector('[data-msg="'+d.message_id+'"]');if(!el)return;let rc=el.querySelector('.mrxn');if(!rc){rc=document.createElement('div');rc.className='mrxn msg-reactions';el.querySelector('.msg-bubble-own,.msg-bubble-other')?.parentElement?.appendChild(rc)}rc.innerHTML=(d.reactions||[]).map(r=>'<span class="rxn-badge '+(r.users.includes(this.me.id)?'own':'')+'" onclick="app.rxn('+d.message_id+',\''+r.emoji+'\')">'+r.emoji+' '+r.count+'</span>').join('')});
    }

    // ══════ NAV ══════
    updateNav(){
        const a=document.getElementById('navAvatar');if(!a)return;
        if(this.me.avatar?.startsWith('emoji:'))a.textContent=this.me.avatar.substring(6);
        else a.innerHTML='<img src="/avatars/'+(this.me.avatar||'default.png')+'">';
        document.querySelectorAll('.sl-link').forEach(l=>l.classList.toggle('active',l.dataset.page===this.page));
    }

    renderSidebar(){
        const p=document.getElementById('slProfile');if(!p)return;
        const nft=this.me.nft_badge?'<span class="nft-badge">'+this.me.nft_badge.emoji+'</span>':'';
        p.innerHTML=this.ava(this.me.avatar,72)+'<div class="sl-name">'+this.esc(this.me.display_name)+nft+'</div><div class="sl-username">@'+this.esc(this.me.username)+'</div><div class="sl-stats"><div class="sl-stat"><strong>'+this.me.followers_count+'</strong><span>'+t('followers')+'</span></div><div class="sl-stat"><strong>'+this.me.following_count+'</strong><span>'+t('following')+'</span></div><div class="sl-stat"><strong>'+this.me.posts_count+'</strong><span>'+t('posts')+'</span></div></div>';
    }

    setupSearch(){
        const inp=document.getElementById('globalSearch');const dd=document.getElementById('searchDropdown');if(!inp||!dd)return;
        let tm;inp.oninput=()=>{clearTimeout(tm);if(inp.value.length<2){dd.classList.remove('open');return}
        tm=setTimeout(async()=>{const r=await fetch('/api/users/search?q='+encodeURIComponent(inp.value));const u=await r.json();if(!u.length){dd.classList.remove('open');return}
        dd.innerHTML=u.slice(0,5).map(x=>'<a class="sd-item" href="/profile/'+x.username+'">'+this.ava(x.avatar,36)+'<div><div style="font-weight:600">'+this.esc(x.display_name)+'</div><div style="color:var(--text2);font-size:12px">@'+this.esc(x.username)+'</div></div></a>').join('');dd.classList.add('open')},300)};
        document.addEventListener('click',e=>{if(!inp.contains(e.target)&&!dd.contains(e.target))dd.classList.remove('open')});
    }

    // ══════ FEED ══════
    cpBox(){return'<div class="create-post-box"><div class="cp-row">'+this.ava(this.me.avatar,44)+'<textarea class="cp-textarea" id="cpT" placeholder="'+t('write_post')+'" rows="2"></textarea></div><div id="cpMP"></div><div class="cp-actions"><button class="cp-btn" onclick="document.getElementById(\'cpF\').click()">📷</button><input type="file" id="cpF" accept="image/*,video/*" style="display:none"><button class="cp-submit" id="cpS">📝 '+t('create_post')+'</button></div></div>'}

    setupCP(){
        let mu=null,mt=null;const fi=document.getElementById('cpF');
        if(fi)fi.onchange=async e=>{const f=e.target.files[0];if(!f)return;const fd=new FormData();fd.append('media',f);const r=await fetch('/api/media',{method:'POST',body:fd});const d=await r.json();if(d.success){mu=d.url;mt=d.type;document.getElementById('cpMP').innerHTML='<div class="cp-media-preview">'+(d.type==='image'?'<img src="'+d.url+'">':'<video src="'+d.url+'" controls>')+'<button class="cp-remove-media" onclick="document.getElementById(\'cpMP\').innerHTML=\'\'">✕</button></div>'}};
        const sub=document.getElementById('cpS');if(sub)sub.onclick=async()=>{const c=document.getElementById('cpT').value.trim();if(!c&&!mu)return;sub.disabled=true;
            const r=await fetch('/api/posts',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({content:c,media_url:mu,media_type:mt})});
            const p=await r.json();sub.disabled=false;document.getElementById('cpT').value='';document.getElementById('cpMP').innerHTML='';mu=null;
            const list=document.getElementById('feedList');if(list)list.insertAdjacentHTML('afterbegin',this.pCard(p))};
    }

    async loadFeed(){const list=document.getElementById('feedList');if(!list)return;const r=await fetch('/api/feed?page='+this.feedPage);const d=await r.json();
        if(!d.posts?.length&&this.feedPage===1){list.innerHTML='<div class="empty-state"><div class="es-icon">📭</div><h3>'+t('no_posts')+'</h3><p>Подпишитесь на кого-нибудь</p></div>';return}
        d.posts.forEach(p=>list.insertAdjacentHTML('beforeend',this.pCard(p)));
        if(d.has_more)list.insertAdjacentHTML('beforeend','<button class="load-more-btn" onclick="app.feedPage++;app.loadFeed()">Ещё</button>')}

    pCard(p){if(!p||p.is_deleted)return'';const a=p.author||{};const nft=a.nft_badge?'<span class="nft-badge" style="font-size:14px">'+a.nft_badge.emoji+'</span>':'';
        let media='';if(p.media_url){if(p.media_type==='image')media='<img src="'+p.media_url+'" class="post-media" loading="lazy">';else if(p.media_type==='video')media='<video src="'+p.media_url+'" class="post-media-video" controls></video>'}
        return'<div class="post-card" data-post-id="'+p.id+'"><div class="post-header"><a class="post-avatar" href="/profile/'+(a.username||'')+'">'+this.ava(a.avatar,44)+'</a><div class="post-meta"><a class="post-author" href="/profile/'+(a.username||'')+'">'+this.esc(a.display_name||'')+nft+'</a><div class="post-time">'+this.fmtT(p.created_at)+'</div></div>'+(a.id===this.me.id?'<div class="post-options" onclick="app.pMenu(event,'+p.id+')">⋯</div>':'')+'</div>'+(p.content?'<div class="post-content">'+this.rtxt(p.content)+'</div>':'')+media+'<div class="post-actions"><button class="pa-btn '+(p.is_liked?'liked':'')+'" onclick="app.like('+p.id+',this)"><svg width="18" height="18" viewBox="0 0 24 24" fill="'+(p.is_liked?'currentColor':'none')+'" stroke="currentColor" stroke-width="2"><path d="M20.84 4.61a5.5 5.5 0 00-7.78 0L12 5.67l-1.06-1.06a5.5 5.5 0 00-7.78 7.78l1.06 1.06L12 21.23l7.78-7.78 1.06-1.06a5.5 5.5 0 000-7.78z"/></svg><span class="pa-count like-count">'+(p.likes_count||0)+'</span></button><button class="pa-btn" onclick="app.tglCmts('+p.id+')"><svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 15a2 2 0 01-2 2H7l-4 4V5a2 2 0 012-2h14a2 2 0 012 2z"/></svg><span class="pa-count">'+(p.comments_count||0)+'</span></button><span class="pa-spacer"></span><button class="pa-btn" onclick="navigator.clipboard.writeText(location.origin+\'/post/'+p.id+'\');app.toast(\''+t('copied')+'\')">↗️</button></div><div id="cm_'+p.id+'"></div></div>'}

    async like(pid,btn){const r=await fetch('/api/posts/'+pid+'/like',{method:'POST'});const d=await r.json();btn.classList.toggle('liked',d.liked);btn.querySelector('svg').setAttribute('fill',d.liked?'currentColor':'none');btn.querySelector('.like-count').textContent=d.likes_count}

    async tglCmts(pid){const sec=document.getElementById('cm_'+pid);if(!sec)return;if(sec.innerHTML){sec.innerHTML='';return}
        const r=await fetch('/api/posts/'+pid+'/comments');const cmts=await r.json();
        sec.innerHTML='<div class="comments-section"><div class="comment-input-row">'+this.ava(this.me.avatar,36)+'<input class="comment-input" id="ci_'+pid+'" placeholder="Комментарий..." onkeydown="if(event.key===\'Enter\')app.addCmt('+pid+')"><button class="comment-send" onclick="app.addCmt('+pid+')">↑</button></div><div id="cl_'+pid+'">'+cmts.map(c=>'<div class="comment-item">'+this.ava(c.author?.avatar,36)+'<div class="comment-bubble"><a class="comment-name" href="/profile/'+(c.author?.username||'')+'">'+this.esc(c.author?.display_name||'')+'</a><div class="comment-text">'+this.esc(c.content)+'</div><div class="comment-time">'+this.fmtT(c.created_at)+'</div></div></div>').join('')+'</div></div>'}

    async addCmt(pid){const inp=document.getElementById('ci_'+pid);if(!inp?.value.trim())return;const r=await fetch('/api/posts/'+pid+'/comments',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({content:inp.value.trim()})});const c=await r.json();inp.value='';document.getElementById('cl_'+pid)?.insertAdjacentHTML('beforeend','<div class="comment-item">'+this.ava(c.author?.avatar,36)+'<div class="comment-bubble"><div class="comment-name">'+this.esc(c.author?.display_name||'')+'</div><div class="comment-text">'+this.esc(c.content)+'</div></div></div>')}

    pMenu(e,pid){e.stopPropagation();const ctx=document.getElementById('ctxMenu');ctx.innerHTML='<div class="ctx-item" onclick="app.delPost('+pid+')">🗑️ '+t('delete')+'</div>';ctx.style.display='block';ctx.style.left=Math.min(e.clientX,innerWidth-180)+'px';ctx.style.top=e.clientY+'px'}
    async delPost(pid){if(!confirm('Удалить?'))return;await fetch('/api/posts/'+pid,{method:'DELETE'});document.querySelector('[data-post-id="'+pid+'"]')?.remove();document.getElementById('ctxMenu').style.display='none'}

    async renderPostPage(pid){const c=document.getElementById('pageContent');const r=await fetch('/api/posts/'+pid);const p=await r.json();if(p.error){c.innerHTML='<div class="empty-state"><h3>Не найден</h3></div>';return}c.innerHTML=this.pCard(p);this.tglCmts(pid)}

    // ══════ STORIES ══════
    async loadStories(){const sb=document.getElementById('storiesBar');const list=document.getElementById('storiesList');if(!sb||!list)return;
        const r=await fetch('/api/stories');const g=await r.json();if(!g.length){sb.style.display='none';return}sb.style.display='';
        let h='<div class="story-add" onclick="app.addStory()"><div class="story-add-icon">+</div><span>История</span></div>';
        g.forEach(gr=>{const u=gr.user;const av=u.avatar?.startsWith('emoji:')?u.avatar.substring(6):'<img src="/avatars/'+(u.avatar||'default.png')+'" style="width:100%;height:100%;object-fit:cover;border-radius:50%">';
            h+='<div class="story-item"><div class="story-ring '+(gr.has_unseen?'':'seen')+'"><div class="story-avatar">'+av+'</div></div><span>'+this.esc((u.display_name||'').substring(0,10))+'</span></div>'});
        list.innerHTML=h}

    addStory(){const inp=document.createElement('input');inp.type='file';inp.accept='image/*,video/*';inp.onchange=async e=>{const f=e.target.files[0];if(!f)return;const fd=new FormData();fd.append('media',f);fd.append('text','');fd.append('bg','#000');await fetch('/api/stories',{method:'POST',body:fd});this.toast('✅');this.loadStories()};inp.click()}

    // ══════ MESSAGES ══════
    msgLayout(){return'<div class="messages-layout"><div class="chat-list-panel"><div class="clp-header"><h3>'+t('messages')+'</h3><button class="btn-sm btn-secondary" onclick="app.newDM()">+</button></div><div class="clp-search"><input type="text" placeholder="Поиск..." id="chSrc" oninput="app.filterCh(this.value)"></div><div class="chat-items" id="chItems"></div></div><div class="chat-view-panel" id="chView"><div class="no-chat"><div class="big-logo">💬</div><h3>'+t('messages')+'</h3><p>Выберите чат</p></div></div></div>'}

    async loadChats(){const r=await fetch('/api/chats');this.chats=await r.json();this.renderCL();for(const c of this.chats)this.socket.emit('join_chat',{chat_id:c.id})}

    renderCL(f){const el=document.getElementById('chItems');if(!el)return;let ch=f?this.chats.filter(c=>(c.name||'').toLowerCase().includes(f.toLowerCase())):this.chats;
        if(!ch.length){el.innerHTML='<div style="text-align:center;padding:40px;color:var(--text2)">'+t('no_chats')+'</div>';return}
        el.innerHTML=ch.map(c=>{const n=c.name||'Chat';const av=this.ava(c.other_user?.avatar||c.avatar,48);const on=c.other_user?.is_online;const lm=c.last_message;const prev=lm?(lm.sender_name+': '+this.trunc(lm.content,25)):'';const tm=lm?this.fmtT(lm.created_at):'';
            return'<div class="chat-item '+(c.id===this.chatId?'active':'')+'" onclick="app.openChat('+c.id+')"><div class="chat-item-avatar">'+av+(on?'<div class="chat-online-dot"></div>':'')+'</div><div class="chat-item-info"><div class="chat-item-top"><span class="chat-item-name">'+this.esc(n)+'</span><span class="chat-item-time">'+tm+'</span></div><div class="chat-item-preview">'+this.esc(prev)+(c.unread_count>0?'<span class="chat-unread">'+c.unread_count+'</span>':'')+'</div></div></div>'}).join('')}

    filterCh(q){this.renderCL(q)}

    async openChat(cid){this.chatId=cid;this.replyTo=null;
        const ch=this.chats.find(c=>c.id===cid);if(!ch)return;
        const panel=document.getElementById('chView');if(!panel)return;
        panel.classList.add('open');
        const n=ch.name||'Chat';const av=this.ava(ch.other_user?.avatar||ch.avatar,40);const on=ch.other_user?.is_online;
        panel.innerHTML='<div class="cvp-header"><button class="cvp-back" onclick="document.getElementById(\'chView\').classList.remove(\'open\');app.chatId=null">←</button><div class="cvp-avatar">'+av+'</div><div class="cvp-info"><h4>'+this.esc(n)+'</h4><div class="cvp-status '+(on?'online':'')+'" id="cvpSt">'+(on?t('online'):'')+'</div></div></div><div class="messages-list" id="mList"></div><div class="msg-input-area" id="mIA"><div class="msg-input-row"><button class="msg-btn" onclick="document.getElementById(\'mFile\').click()">📎</button><input type="file" id="mFile" style="display:none" onchange="app.sendMF(this)"><textarea class="msg-input" id="mInp" placeholder="Сообщение..." rows="1" onkeydown="if(event.key===\'Enter\'&&!event.shiftKey){event.preventDefault();app.sendM()}" oninput="app.emTyp()"></textarea><button class="msg-send" onclick="app.sendM()">→</button></div></div>';
        const r=await fetch('/api/chats/'+cid+'/messages');const d=await r.json();
        const list=document.getElementById('mList');if(list){list.innerHTML=d.messages.map(m=>this.mEl(m)).join('');list.scrollTop=list.scrollHeight}
        this.renderCL();
        const unr=d.messages.filter(m=>m.sender_id!==this.me.id&&!m.read_by.some(r=>r.user_id===this.me.id)).map(m=>m.id);
        if(unr.length)this.socket.emit('mark_read',{chat_id:cid,message_ids:unr});
        this.socket.emit('join_chat',{chat_id:cid});document.getElementById('mInp')?.focus()}

    mEl(m){const own=m.sender_id===this.me.id;const av=this.ava(m.sender_avatar,30);const myAv=this.ava(this.me.avatar,30);
        const chk=own?'<span class="chk '+(m.read_by.filter(r=>r.user_id!==this.me.id).length>0?'read':'sent')+'">'+(m.read_by.filter(r=>r.user_id!==this.me.id).length>0?'✓✓':'✓')+'</span>':'';
        let cnt='';
        if(m.is_deleted)cnt='<div class="mtxt" style="opacity:.5;font-style:italic">'+t('deleted')+'</div>';
        else if(m.message_type==='sticker')cnt='<div class="msg-sticker">'+m.content+'</div>';
        else if(m.media_url)cnt=(m.media_type==='image'?'<img src="'+m.media_url+'" class="msg-media">':'<a href="'+m.media_url+'" target="_blank">📎</a>')+(m.content?'<div class="mtxt">'+this.esc(m.content)+'</div>':'');
        else if(m.voice_url)cnt='<div class="voice-msg"><button class="voice-play" onclick="const a=this.nextElementSibling;a.paused?a.play():a.pause();this.textContent=a.paused?\'▶️\':\'⏸️\'">▶️</button><audio src="'+m.voice_url+'" preload="metadata"></audio></div>';
        else cnt='<div class="mtxt">'+this.rtxt(m.content)+'</div>';
        const rp=m.reply_to?'<div class="reply-preview"><div class="rp-name">'+this.esc(m.reply_to.sender_name)+'</div><div class="rp-text">'+this.esc(m.reply_to.content)+'</div></div>':'';
        const fwd=m.forwarded_from_name?'<div class="fwd-label">↗️ '+this.esc(m.forwarded_from_name)+'</div>':'';
        const ed=m.edited_at?'<span style="font-size:10px;color:var(--text3)">('+t('edited')+')</span>':'';
        const rxn=m.reactions?.length?'<div class="mrxn msg-reactions">'+m.reactions.map(r=>'<span class="rxn-badge '+(r.users.includes(this.me.id)?'own':'')+'" onclick="app.rxn('+m.id+',\''+r.emoji+'\')">'+r.emoji+' '+r.count+'</span>').join('')+'</div>':'';
        return'<div class="message '+(own?'own':'other')+'" data-msg="'+m.id+'" oncontextmenu="app.mCtx(event,'+m.id+','+own+')">'+(own?'':'<div class="msg-avatar">'+av+'</div>')+'<div><div class="'+(own?'msg-bubble-own':'msg-bubble-other')+'">'+fwd+rp+cnt+'<div class="msg-meta">'+ed+'<span class="msg-time">'+this.fmtM(m.created_at)+'</span>'+chk+'</div></div>'+rxn+'</div>'+(own?'<div class="msg-avatar">'+myAv+'</div>':'')+'</div>'}

    mCtx(e,mid,own){e.preventDefault();const ctx=document.getElementById('ctxMenu');
        let items='<div class="ctx-item" onclick="app.replyM('+mid+')">↩️ '+t('reply')+'</div>';
        items+='<div class="ctx-item" onclick="app.rxnMenu('+mid+')">😊 Реакция</div>';
        if(own)items+='<div class="ctx-item danger" onclick="app.delM('+mid+')">🗑️ '+t('delete')+'</div>';
        ctx.innerHTML=items;ctx.style.display='block';ctx.style.left=Math.min(e.clientX,innerWidth-180)+'px';ctx.style.top=Math.min(e.clientY,innerHeight-120)+'px'}

    replyM(mid){document.getElementById('ctxMenu').style.display='none';this.replyTo=mid;const area=document.getElementById('mIA');if(!area)return;let rb=document.getElementById('rBar');if(rb)rb.remove();rb=document.createElement('div');rb.id='rBar';rb.className='reply-bar';rb.innerHTML='<div class="reply-bar-info"><div class="reply-bar-name">↩️</div></div><button class="reply-bar-close" onclick="app.cancelR()">✕</button>';area.insertBefore(rb,area.firstChild);document.getElementById('mInp')?.focus()}
    cancelR(){this.replyTo=null;document.getElementById('rBar')?.remove()}

    rxnMenu(mid){document.getElementById('ctxMenu').style.display='none';const emojis=['👍','❤️','😂','😮','😢','🔥','👏','🎉'];const ctx=document.getElementById('ctxMenu');ctx.innerHTML=emojis.map(e=>'<div class="ctx-item" onclick="app.rxn('+mid+',\''+e+'\')">'+e+'</div>').join('');ctx.style.display='block'}
    rxn(mid,emoji){this.socket.emit('add_reaction',{message_id:mid,emoji});document.getElementById('ctxMenu').style.display='none'}
    delM(mid){document.getElementById('ctxMenu').style.display='none';this.socket.emit('delete_message',{message_id:mid,chat_id:this.chatId})}

    sendM(){const inp=document.getElementById('mInp');if(!inp?.value.trim())return;
        const d={chat_id:this.chatId,content:inp.value.trim(),type:'text'};
        if(this.replyTo){d.reply_to_id=this.replyTo;this.cancelR()}
        this.socket.emit('send_message',d);inp.value='';inp.style.height='auto';this.socket.emit('stop_typing',{chat_id:this.chatId})}

    emTyp(){if(!this.chatId)return;this.socket.emit('typing',{chat_id:this.chatId});if(this.typingTm)clearTimeout(this.typingTm);this.typingTm=setTimeout(()=>this.socket.emit('stop_typing',{chat_id:this.chatId}),2000)}

    async sendMF(inp){const f=inp.files[0];if(!f)return;const fd=new FormData();fd.append('media',f);const r=await fetch('/api/media',{method:'POST',body:fd});const d=await r.json();if(d.success)this.socket.emit('send_message',{chat_id:this.chatId,content:f.name,media_url:d.url,media_type_hint:d.type,type:d.type});inp.value=''}

    onMsg(m){if(m.chat_id===this.chatId){const list=document.getElementById('mList');if(list){list.insertAdjacentHTML('beforeend',this.mEl(m));list.scrollTop=list.scrollHeight}if(m.sender_id!==this.me.id)this.socket.emit('mark_read',{chat_id:m.chat_id,message_ids:[m.id]});document.getElementById('typInd')?.remove()}this.loadChats()}

    newDM(){const q=prompt('Юзернейм:');if(!q)return;fetch('/api/users/search?q='+encodeURIComponent(q)).then(r=>r.json()).then(u=>{if(u.length)this.startDM(u[0].id);else this.toast('Не найден')})}
    async startDM(uid){const r=await fetch('/api/chats/dm',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({user_id:uid})});const ch=await r.json();await this.loadChats();this.openChat(ch.id)}

    // ══════ NOTIFICATIONS ══════
    async loadNotifs(){const r=await fetch('/api/notifications');const n=await r.json();fetch('/api/notifications/read',{method:'POST'});
        const el=document.getElementById('notifList');if(!el)return;
        if(!n.length){el.innerHTML='<div class="empty-state"><div class="es-icon">🔔</div><h3>Нет уведомлений</h3></div>';return}
        el.innerHTML=n.map(x=>{const u=x.from_user;const av=u?this.ava(u.avatar,44):'';const icons={like:'❤️',comment:'💬',follow:'👤',repost:'🔁',message:'✉️'};
            return'<a class="notif-item '+(x.is_read?'':'unread')+'" href="'+(x.link||'#')+'">'+av+'<div class="notif-text"><strong>'+this.esc(u?.display_name||'')+'</strong> '+this.esc(x.text||'')+'<div class="notif-time">'+this.fmtT(x.created_at)+'</div></div><div class="notif-icon">'+(icons[x.type]||'🔔')+'</div></a>'}).join('')}

    async updateBadges(){const r=await fetch('/api/notifications/count');const d=await r.json();const c=d.count||0;
        ['notifBadge','slNotifBadge','mnNotifBadge'].forEach(id=>{const el=document.getElementById(id);if(el){el.style.display=c>0?'flex':'none';el.textContent=c}});
        document.title=c>0?'('+c+') Gyert':'Gyert'}

    // ══════ PROFILE ══════
    async renderProfile(username){const c=document.getElementById('pageContent');
        const r=await fetch('/api/users/'+username);if(!r.ok){c.innerHTML='<div class="empty-state"><h3>Не найден</h3></div>';return}
        const u=await r.json();const isMe=u.id===this.me.id;const nft=u.nft_badge?'<span class="nft-badge">'+u.nft_badge.emoji+'</span>':'';
        const bigAva=u.avatar?.startsWith('emoji:')?'<div style="font-size:48px">'+u.avatar.substring(6)+'</div>':'<img src="/avatars/'+(u.avatar||'default.png')+'" style="width:100%;height:100%;object-fit:cover">';
        const cover=u.cover_image?'<img src="'+u.cover_image+'" style="width:100%;height:100%;object-fit:cover">':'';
        let btns=isMe?'<button class="btn-primary" onclick="app.editProf()">'+t('edit_profile')+'</button>':'<button class="btn-primary" id="fBtn_'+u.id+'" onclick="app.tglFollow('+u.id+')">'+(u.is_following?t('unfollow'):t('follow'))+'</button><button class="btn-secondary" onclick="app.startDM('+u.id+')">💬</button>';
        c.innerHTML='<div class="profile-page"><div class="profile-cover">'+cover+'</div><div class="profile-info-row"><div class="profile-avatar-wrap"><div class="profile-big-avatar">'+bigAva+'</div></div><div class="profile-name-row"><span class="profile-name">'+this.esc(u.display_name||'')+nft+'</span><span class="profile-username">@'+this.esc(u.username)+'</span></div>'+(u.bio?'<div class="profile-bio">'+this.rtxt(u.bio)+'</div>':'')+'<div class="profile-stats"><div class="pstat"><strong>'+(u.followers_count||0)+'</strong><span>'+t('followers')+'</span></div><div class="pstat"><strong>'+(u.following_count||0)+'</strong><span>'+t('following')+'</span></div><div class="pstat"><strong>'+(u.posts_count||0)+'</strong><span>'+t('posts')+'</span></div></div><div class="profile-actions">'+btns+'</div></div><div id="pPosts" style="margin-top:16px"></div></div>';
        const pr=await fetch('/api/users/'+username+'/posts');const pd=await pr.json();
        const pp=document.getElementById('pPosts');if(pp)pd.posts?.forEach(post=>pp.insertAdjacentHTML('beforeend',this.pCard(post)))}

    async tglFollow(uid){const r=await fetch('/api/users/'+uid+'/follow',{method:'POST'});const d=await r.json();const btn=document.getElementById('fBtn_'+uid);if(btn)btn.textContent=d.following?t('unfollow'):t('follow')}

    editProf(){this.openModal('<div class="modal-header"><h2>'+t('edit_profile')+'</h2><button class="modal-close" onclick="app.closeModal()">✕</button></div><div class="modal-body"><div class="field"><label>Имя</label><input type="text" id="epN" value="'+this.esc(this.me.display_name||'')+'"></div><div class="field"><label>О себе</label><textarea id="epB" rows="3">'+this.esc(this.me.bio||'')+'</textarea></div><div class="field"><label>Город</label><input type="text" id="epL" value="'+this.esc(this.me.location||'')+'"></div><div class="field"><label>Сайт</label><input type="url" id="epW" value="'+this.esc(this.me.website||'')+'"></div></div><div class="modal-footer"><button class="btn-primary" onclick="app.saveProf()">'+t('save')+'</button></div>')}

    async saveProf(){const d={display_name:document.getElementById('epN')?.value,bio:document.getElementById('epB')?.value,location:document.getElementById('epL')?.value,website:document.getElementById('epW')?.value};const r=await fetch('/api/settings',{method:'PUT',headers:{'Content-Type':'application/json'},body:JSON.stringify(d)});const res=await r.json();if(res.success){this.me=res.user;this.updateNav();
        if(this.me.email && !this.me.email_verified){const b=document.getElementById('verifyBanner');if(b)b.style.display='flex'}this.renderSidebar();this.closeModal();this.toast('✅')}}

    // ══════ SEARCH ══════
    async searchP(q){if(q.length<2){document.getElementById('spRes').innerHTML='';return}const r=await fetch('/api/users/search?q='+encodeURIComponent(q));const u=await r.json();document.getElementById('spRes').innerHTML=u.map(x=>'<a class="search-user-item" href="/profile/'+x.username+'">'+this.ava(x.avatar,44)+'<div style="flex:1"><div style="font-weight:700">'+this.esc(x.display_name)+'</div><div style="color:var(--acc);font-size:13px">@'+this.esc(x.username)+'</div></div></a>').join('')}

    // ══════ REELS ══════
    async loadReels(){const c=document.getElementById('reelsC');if(!c)return;const r=await fetch('/api/reels/all');const d=await r.json();if(!d.posts?.length){c.innerHTML='<div class="empty-state"><div class="es-icon">🎬</div><h3>Нет контента</h3><p>Создайте пост с фото!</p></div>';return}
        c.innerHTML=d.posts.map(p=>{const a=p.author||{};let media='';if(p.media_url){if(p.media_type==='video')media='<video class="reel-video" src="'+p.media_url+'" loop playsinline muted onclick="this.paused?this.play():this.pause()"></video>';else media='<img class="reel-image" src="'+p.media_url+'" loading="lazy">'}
            return'<div class="reel-card">'+media+'<div class="reel-overlay"><div class="reel-content">'+(p.content?'<p style="color:#fff;font-size:15px;text-shadow:0 1px 4px rgba(0,0,0,.5)">'+this.esc(p.content.substring(0,200))+'</p>':'')+'</div><div class="reel-sidebar"><div class="reel-action" onclick="app.like('+p.id+',this)"><div class="reel-action-icon">❤️</div><span class="like-count">'+(p.likes_count||0)+'</span></div><div class="reel-action" onclick="navigator.clipboard.writeText(location.origin+\'/post/'+p.id+'\');app.toast(\'Copied!\')"><div class="reel-action-icon">↗️</div></div></div><a class="reel-author" href="/profile/'+(a.username||'')+'">'+this.ava(a.avatar,40)+'<div class="reel-author-info"><strong>'+this.esc(a.display_name||'')+'</strong><span>@'+this.esc(a.username||'')+'</span></div></a></div></div>'}).join('');
        const obs=new IntersectionObserver(entries=>{entries.forEach(entry=>{const v=entry.target.querySelector('.reel-video');if(v){if(entry.isIntersecting)v.play().catch(()=>{});else v.pause()}})},{threshold:.5});c.querySelectorAll('.reel-card').forEach(card=>obs.observe(card))}

    // ══════ AI ══════
    aiPage(){return'<div class="ai-page"><div style="text-align:center;padding:24px 0"><div style="font-size:56px">🤖</div><h2 style="font-size:24px;background:var(--grad);-webkit-background-clip:text;-webkit-text-fill-color:transparent">GyertAI</h2><p style="color:var(--text2)">Умный помощник</p></div><div class="ai-chat" id="aiChat" style="flex:1;overflow-y:auto;padding:16px;background:var(--card);border:1px solid var(--border);border-radius:20px;margin:12px 0;display:flex;flex-direction:column;gap:12px;min-height:300px"><div style="display:flex;gap:10px;max-width:85%"><div style="font-size:24px">🤖</div><div style="padding:12px 16px;background:var(--bg4);border:1px solid var(--border);border-radius:18px;font-size:14px;line-height:1.6">Привет! Я GyertAI. Задайте мне любой вопрос!</div></div></div><div style="display:flex;gap:10px"><input type="text" id="aiInp" placeholder="Спросите..." style="flex:1;padding:12px 18px;background:var(--bg4);border:1px solid var(--border);border-radius:24px;color:var(--text);font-size:15px;outline:none" onkeydown="if(event.key===\'Enter\')app.sendAI()"><button class="msg-send" onclick="app.sendAI()">→</button></div></div>'}

    async sendAI(){const inp=document.getElementById('aiInp');const chat=document.getElementById('aiChat');if(!inp||!chat)return;const q=inp.value.trim();if(!q)return;inp.value='';
        chat.innerHTML+='<div style="display:flex;gap:10px;max-width:85%;align-self:flex-end;flex-direction:row-reverse"><div style="font-size:16px">'+this.ava(this.me.avatar,32)+'</div><div style="padding:12px 16px;background:linear-gradient(135deg,rgba(77,124,255,.2),rgba(255,59,111,.12));border:1px solid rgba(77,124,255,.15);border-radius:18px;font-size:14px">'+this.esc(q)+'</div></div>';chat.scrollTop=chat.scrollHeight;
        const thId='th_'+Date.now();chat.innerHTML+='<div id="'+thId+'" style="display:flex;gap:10px;max-width:85%"><div style="font-size:24px">🤖</div><div style="padding:12px 16px;background:var(--bg4);border:1px solid var(--border);border-radius:18px;font-size:14px"><span class="typing-ind"><span></span><span></span><span></span></span></div></div>';chat.scrollTop=chat.scrollHeight;
        try{const r=await fetch('/api/ai/chat',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({message:q})});const d=await r.json();
            const el=document.getElementById(thId);if(el){const bub=el.querySelector('div:last-child');if(bub){bub.innerHTML=this.rtxt(d.response||'Нет ответа');if(d.model&&d.model!=='demo'&&d.model!=='error')bub.innerHTML+='<div style="font-size:10px;color:var(--text3);margin-top:6px">'+d.model+'</div>'}chat.scrollTop=chat.scrollHeight}
        }catch(e){const el=document.getElementById(thId);if(el)el.querySelector('div:last-child').textContent='Ошибка соединения'}}

    // ══════ RECOMMENDED ══════
    async loadRecommended(){const el=document.getElementById('recommendedList');if(!el)return;const r=await fetch('/api/users/recommended');const u=await r.json();el.innerHTML=u.map(x=>'<div class="rec-item">'+this.ava(x.avatar,40)+'<div class="rec-info"><a class="rec-name" href="/profile/'+x.username+'">'+this.esc(x.display_name)+'</a><div class="rec-username">@'+this.esc(x.username)+'</div></div><button class="btn-follow" id="rf_'+x.id+'" onclick="app.tglFollow('+x.id+')">'+t('follow')+'</button></div>').join('')}

    // ══════ NFT ══════
    showNftInfo(nft){if(!nft)return;this.openModal('<div class="modal-body" style="text-align:center;padding:32px"><div style="font-size:80px;margin-bottom:16px">'+nft.emoji+'</div><h2>'+this.esc(nft.name)+'</h2><div style="font-size:24px;font-weight:800;color:var(--acc);margin:8px 0">'+this.esc(nft.price)+'</div><div style="font-size:13px;color:var(--text2)">'+this.esc(nft.index)+'</div></div>')}

    async activateNft(){const code=document.getElementById('nftInp')?.value?.trim();if(!code)return;const r=await fetch('/api/nft/activate',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({code})});const d=await r.json();if(d.success){this.toast('✅ NFT: '+d.nft?.nft_emoji);const mr=await fetch('/api/me');this.me=await mr.json();this.updateNav();
        if(this.me.email && !this.me.email_verified){const b=document.getElementById('verifyBanner');if(b)b.style.display='flex'}this.renderSidebar()}else this.toast('❌ '+(d.error||'Ошибка'))}

    // ══════ SETTINGS ══════
    openSettings(){document.getElementById('userMenu').classList.remove('open');
        this.openModal('<div class="modal-header"><h2>⚙️ '+t('settings')+'</h2><button class="modal-close" onclick="app.closeModal()">✕</button></div><div class="modal-body"><div style="margin-bottom:16px"><div style="font-size:12px;font-weight:700;color:var(--text2);text-transform:uppercase;margin-bottom:8px">Тема</div><div style="display:grid;grid-template-columns:repeat(3,1fr);gap:6px">'+['dark','light','midnight','ocean','office'].map(th=>'<button style="padding:8px;background:var(--bg4);border:2px solid '+(this.me.theme===th?'var(--acc)':'var(--border)')+';border-radius:8px;color:var(--text);cursor:pointer;font-size:12px" onclick="app.applyTheme(\''+th+'\');fetch(\'/api/settings\',{method:\'PUT\',headers:{\'Content-Type\':\'application/json\'},body:JSON.stringify({theme:\''+th+'\'})})">'+th+'</button>').join('')+'</div></div><div style="margin-bottom:16px"><div style="font-size:12px;font-weight:700;color:var(--text2);text-transform:uppercase;margin-bottom:8px">NFT</div><div style="display:flex;gap:8px"><input type="text" id="nftInp" placeholder="Код" style="flex:1;padding:8px 12px;background:var(--bg4);border:1px solid var(--border);border-radius:8px;color:var(--text);outline:none"><button class="btn-primary btn-sm" onclick="app.activateNft()">OK</button></div>'+(this.me.nft_badge?'<div style="margin-top:6px;font-size:13px;color:var(--text2)">Текущий: '+this.me.nft_badge.emoji+' '+this.esc(this.me.nft_badge.name)+'</div>':'')+'</div><button class="btn-secondary" onclick="app.editProf();app.closeModal()" style="width:100%;margin-bottom:8px">✏️ '+t('edit_profile')+'</button></div><div class="modal-footer"><button style="padding:8px 16px;background:none;border:1px solid #ff3b3b;border-radius:8px;color:#ff3b3b;cursor:pointer" onclick="app.logout()">🚪 '+t('logout')+'</button></div>')}

    // ══════ THEME ══════
    applyTheme(th){document.body.className=document.body.className.replace(/theme-\w+/g,'')+' theme-'+th;this.me.theme=th;document.querySelectorAll('.th-btn').forEach(b=>b.classList.toggle('active',b.dataset.theme===th))}

    // ══════ MODAL ══════
    openModal(html){document.getElementById('modalBox').innerHTML=html;document.getElementById('modalOverlay').style.display='flex';document.getElementById('modalOverlay').onclick=e=>{if(e.target===document.getElementById('modalOverlay'))this.closeModal()}}
    closeModal(){document.getElementById('modalOverlay').style.display='none'}

    // ══════ UTILS ══════
    ava(avatar,sz){sz=sz||44;const s='width:'+sz+'px;height:'+sz+'px;border-radius:50%;overflow:hidden;display:inline-flex;align-items:center;justify-content:center;background:var(--bg3);font-size:'+Math.round(sz*.45)+'px;flex-shrink:0';if(!avatar||avatar==='default.png')return'<div style="'+s+'"><img src="/avatars/default.png" style="width:100%;height:100%;object-fit:cover"></div>';if(avatar.startsWith('emoji:'))return'<div style="'+s+'">'+avatar.substring(6)+'</div>';return'<div style="'+s+'"><img src="/avatars/'+avatar+'" style="width:100%;height:100%;object-fit:cover" onerror="this.outerHTML=\'😊\'"></div>'}
    rtxt(text){if(!text)return'';let t=this.esc(text);t=t.replace(/\*\*(.*?)\*\*/g,'<strong>$1</strong>');t=t.replace(/\*(.*?)\*/g,'<em>$1</em>');t=t.replace(/@([a-zA-Z0-9_]+)/g,'<a href="/profile/$1" style="color:var(--acc)">@$1</a>');t=t.replace(/(https?:\/\/[^\s]+)/g,'<a href="$1" target="_blank" style="color:var(--acc)">$1</a>');return t}
    toL(iso){if(!iso)return null;if(!iso.endsWith('Z')&&!iso.includes('+'))iso+='Z';return new Date(iso)}
    fmtT(iso){const d=this.toL(iso);if(!d)return'';const n=new Date();if(n-d<86400000&&d.getDate()===n.getDate())return d.toLocaleTimeString([],{hour:'2-digit',minute:'2-digit'});if(n-d<604800000)return d.toLocaleDateString([],{weekday:'short'});return d.toLocaleDateString([],{day:'2-digit',month:'2-digit'})}
    fmtM(iso){const d=this.toL(iso);return d?d.toLocaleTimeString([],{hour:'2-digit',minute:'2-digit'}):''}
    fmtL(iso){const d=this.toL(iso);if(!d)return'';const s=Math.floor((new Date()-d)/1000);if(s<60)return'сейчас';if(s<3600)return Math.floor(s/60)+'м';if(s<86400)return Math.floor(s/3600)+'ч';return d.toLocaleDateString([],{day:'numeric',month:'short'})}
    trunc(s,n){return!s?'':s.length>n?s.substring(0,n)+'...':s}
    esc(t){if(!t)return'';const d=document.createElement('div');d.textContent=t;return d.innerHTML}
    toast(msg){const el=document.getElementById('toast');el.textContent=msg;el.classList.add('show');clearTimeout(el._t);el._t=setTimeout(()=>el.classList.remove('show'),3000)}
    async logout(){await fetch('/api/logout',{method:'POST'});location.href='/login'}
}

window.addEventListener('DOMContentLoaded',()=>{window.app=new App()});