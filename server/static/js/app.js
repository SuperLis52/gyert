const LANGS={ru:{feed:'Лента',messages:'Сообщения',notifications:'Уведомления',profile:'Профиль',search:'Поиск',reels:'Reels',music:'Музыка',ai:'GyertAI',settings:'Настройки',logout:'Выйти',follow:'Подписаться',unfollow:'Отписаться',like:'Нравится',comment:'Комментировать',send:'Отправить',reply:'Ответить',edit:'Редактировать',delete:'Удалить',save:'Сохранить',cancel:'Отмена',online:'в сети',typing:'печатает',today:'Сегодня',yesterday:'Вчера',no_posts:'Нет постов',no_chats:'Нет сообщений',write_post:'Что у вас нового?',new_chat:'Новый чат',new_group:'Новая группа',create_post:'Опубликовать',followers:'подписчиков',following:'подписок',posts:'постов',edit_profile:'Редактировать',nft_code:'Код NFT',activate:'Активировать',theme:'Тема',language:'Язык',copied:'Скопировано!',deleted:'Удалено',edited:'ред.',dark:'🌙 Тёмная',light:'☀️ Светлая',midnight:'🌌 Midnight',ocean:'🌊 Ocean',office:'💼 Офис'},en:{feed:'Feed',messages:'Messages',notifications:'Notifications',profile:'Profile',search:'Search',reels:'Reels',music:'Music',ai:'GyertAI',settings:'Settings',logout:'Logout',follow:'Follow',unfollow:'Unfollow',like:'Like',comment:'Comment',send:'Send',reply:'Reply',edit:'Edit',delete:'Delete',save:'Save',cancel:'Cancel',online:'online',typing:'typing',today:'Today',yesterday:'Yesterday',no_posts:'No posts',no_chats:'No messages',write_post:"What's new?",new_chat:'New chat',new_group:'New group',create_post:'Post',followers:'followers',following:'following',posts:'posts',edit_profile:'Edit',nft_code:'NFT Code',activate:'Activate',theme:'Theme',language:'Language',copied:'Copied!',deleted:'Deleted',edited:'edited',dark:'🌙 Dark',light:'☀️ Light',midnight:'🌌 Midnight',ocean:'🌊 Ocean',office:'💼 Office'}};
let T=LANGS.ru;
function t(k){return T[k]||k}
function setLang(l){T=LANGS[l]||LANGS.ru;localStorage.setItem('gyert_lang',l)}
function getLang(){const s=localStorage.getItem('gyert_lang');return s&&LANGS[s]?s:'ru'}

function toggleUserMenu(){document.getElementById('userMenu').classList.toggle('open')}

class GyertApp{
    constructor(){
        this.me=null;
        this.socket=null;
        this.page=document.body.dataset.page||'feed';
        this.currentChatId=null;
        this.chats=[];
        this.typingTimeout=null;
        this.replyingTo=null;
        this.editingMsgId=null;
        this.feedPage=1;
        this.contactNames=JSON.parse(localStorage.getItem('gyert_cnames')||'{}');
        this.init();
    }

    async init(){
        setLang(getLang());
        try{
            const r=await fetch('/api/me');
            if(!r.ok){window.location.href='/login';return}
            this.me=await r.json();
        }catch(e){window.location.href='/login';return}

        this.applyTheme(this.me.theme||'dark');
        this.setupSocket();
        this.updateNavAvatar();
        this.renderSidebar();
        this.highlightNav();

        // Load current page content
        await this.loadCurrentPage();

        // Load extras
        this.loadRecommended();
        this.updateBadges();
        setInterval(()=>this.updateBadges(),15000);

        // Close menus on click outside
        document.addEventListener('click',e=>{
            const um=document.getElementById('userMenu');
            const naw=document.getElementById('navAvatarWrap');
            if(um&&naw&&!um.contains(e.target)&&!naw.contains(e.target))um.classList.remove('open');
            const ctx=document.getElementById('ctxMenu');
            if(ctx)ctx.style.display='none';
        });

        // Global search
        this.setupGlobalSearch();

        // Theme buttons
        document.querySelectorAll('.th-btn').forEach(b=>{
            b.addEventListener('click',()=>{
                document.querySelectorAll('.th-btn').forEach(x=>x.classList.remove('active'));
                b.classList.add('active');
                this.applyTheme(b.dataset.theme);
                fetch('/api/settings',{method:'PUT',headers:{'Content-Type':'application/json'},body:JSON.stringify({theme:b.dataset.theme})});
            });
        });
    }

    highlightNav(){
        document.querySelectorAll('.sl-link').forEach(a=>a.classList.toggle('active',a.dataset.page===this.page));
        document.querySelectorAll('.nav-btn').forEach(b=>{
            const id=b.id.replace('nav','').toLowerCase();
            b.classList.toggle('active',this.page.startsWith(id));
        });
    }

    // ─── LOAD PAGE BASED ON data-page ─────────────────────────
    async loadCurrentPage(){
        const c=document.getElementById('pageContent');
        if(!c)return;
        const sb=document.getElementById('storiesBar');
        const sr=document.getElementById('sidebarRight');

        switch(this.page){
            case 'feed':
                if(sb)sb.style.display='';
                if(sr)sr.style.display='';
                c.innerHTML=this.createPostBox()+'<div id="feedList"></div>';
                this.setupCreatePost();
                await this.loadFeed();
                await this.loadStories();
                break;
            case 'messages':
                if(sb)sb.style.display='none';
                if(sr)sr.style.display='none';
                c.innerHTML=this.messagesHTML();
                await this.loadChats();
                const params=new URLSearchParams(window.location.search);
                if(params.get('chat'))setTimeout(()=>this.openChat(parseInt(params.get('chat'))),300);
                break;
            case 'notifications':
                if(sb)sb.style.display='none';
                if(sr)sr.style.display='';
                c.innerHTML='<div class="notif-list" id="notifList"></div>';
                await this.loadNotifications();
                break;
            case 'profile':
                if(sb)sb.style.display='none';
                if(sr)sr.style.display='';
                const target=document.body.dataset.target||this.me.username;
                await this.renderProfile(target);
                break;
            case 'search':
                if(sb)sb.style.display='none';
                if(sr)sr.style.display='';
                c.innerHTML='<div class="search-page"><input type="text" placeholder="Поиск людей..." id="searchPageInput"><div id="searchPageResults"></div></div>';
                document.getElementById('searchPageInput').oninput=e=>this.searchPage(e.target.value);
                document.getElementById('searchPageInput').focus();
                break;
            case 'reels':
                if(sb)sb.style.display='none';
                if(sr)sr.style.display='none';
                c.innerHTML='<div id="reelsContainer" class="reels-container"></div>';
                await this.loadReels();
                break;
            case 'music':
                if(sb)sb.style.display='none';
                if(sr)sr.style.display='none';
                c.innerHTML='<div class="empty-state"><div class="es-icon">🎵</div><h3>Gyert Music</h3><p>Скоро! Интеграция с музыкальными сервисами</p></div>';
                break;
            case 'ai':
                if(sb)sb.style.display='none';
                if(sr)sr.style.display='none';
                c.innerHTML=this.renderAIPage();
                break;
            case 'post':
                if(sb)sb.style.display='none';
                if(sr)sr.style.display='';
                const pid=document.body.dataset.postId;
                if(pid)await this.renderPostPage(parseInt(pid));
                break;
            default:
                if(sb)sb.style.display='';
                c.innerHTML='<div class="empty-state"><h3>Страница не найдена</h3></div>';
        }
    }

    // ─── SOCKET ───────────────────────────────────────────────
    setupSocket(){
        this.socket=io();
        this.socket.on('new_message',d=>this.onNewMessage(d));
        this.socket.on('message_edited',d=>{const el=document.querySelector('[data-msg-id="'+d.id+'"] .msg-text');if(el)el.textContent=d.content});
        this.socket.on('message_deleted',d=>{const el=document.querySelector('[data-msg-id="'+d.message_id+'"] .msg-text');if(el){el.textContent=t('deleted');el.style.opacity='.5'}});
        this.socket.on('reaction_updated',d=>this.onReaction(d));
        this.socket.on('messages_read',d=>{if(d.chat_id===this.currentChatId)d.message_ids.forEach(mid=>{const el=document.querySelector('[data-msg-id="'+mid+'"] .read-checks');if(el){el.className='read-checks read';el.textContent='✓✓'}})});
        this.socket.on('user_typing',d=>{if(d.chat_id===this.currentChatId){let ti=document.getElementById('typingInd');if(!ti){ti=document.createElement('div');ti.id='typingInd';ti.className='typing-ind';document.getElementById('msgList')?.appendChild(ti)}ti.innerHTML=this.esc(d.display_name)+' '+t('typing')+' <span></span><span></span><span></span>'}});
        this.socket.on('user_stop_typing',d=>{if(d.chat_id===this.currentChatId)document.getElementById('typingInd')?.remove()});
        this.socket.on('user_status',d=>{const st=document.getElementById('cvpStatus');if(st&&this.currentChatId){const ch=this.chats.find(c=>c.id===this.currentChatId);if(ch?.other_user?.id===d.user_id){st.className='cvp-status '+(d.is_online?'online':'');st.textContent=d.is_online?t('online'):this.fmtLast(d.last_seen)}}});
        this.socket.on('notification',d=>{this.showToast('🔔 '+(d.text||''));this.updateBadges()});
        this.socket.on('chat_created',()=>{if(this.page==='messages')this.loadChats()});
        this.socket.on('post_liked',d=>{const el=document.querySelector('[data-post-id="'+d.post_id+'"] .like-count');if(el)el.textContent=d.likes_count});
    }

    // ─── NAV ──────────────────────────────────────────────────
    updateNavAvatar(){
        const a=document.getElementById('navAvatar');
        if(!a)return;
        if(this.me.avatar?.startsWith('emoji:'))a.textContent=this.me.avatar.substring(6);
        else a.innerHTML='<img src="/avatars/'+(this.me.avatar||'default.png')+'" onerror="this.src=\'/avatars/default.png\'">';
    }

    renderSidebar(){
        const p=document.getElementById('slProfile');
        if(!p)return;
        const nft=this.me.nft_badge?'<span class="nft-badge" onclick="app.showNftInfo('+JSON.stringify(this.me.nft_badge).replace(/"/g,'&quot;')+')">'+this.me.nft_badge.emoji+'</span>':'';
        p.innerHTML=this.avatarHtml(this.me.avatar,72)+'<div class="sl-name">'+this.esc(this.me.display_name)+nft+'</div><div class="sl-username">@'+this.esc(this.me.username)+'</div><div class="sl-stats"><div class="sl-stat"><strong>'+this.me.followers_count+'</strong><span>'+t('followers')+'</span></div><div class="sl-stat"><strong>'+this.me.following_count+'</strong><span>'+t('following')+'</span></div><div class="sl-stat"><strong>'+this.me.posts_count+'</strong><span>'+t('posts')+'</span></div></div>';
    }

    setupGlobalSearch(){
        const inp=document.getElementById('globalSearch');
        const dd=document.getElementById('searchDropdown');
        if(!inp||!dd)return;
        let timer;
        inp.oninput=()=>{clearTimeout(timer);if(inp.value.length<2){dd.classList.remove('open');return}
            timer=setTimeout(async()=>{const r=await fetch('/api/users/search?q='+encodeURIComponent(inp.value));const users=await r.json();if(!users.length){dd.classList.remove('open');return}
            dd.innerHTML=users.slice(0,5).map(u=>'<a class="sd-item" href="/profile/'+u.username+'">'+this.avatarHtml(u.avatar,36)+'<div><div style="font-weight:600;font-size:14px">'+this.esc(u.display_name)+'</div><div style="color:var(--text2);font-size:12px">@'+this.esc(u.username)+'</div></div></a>').join('');
            dd.classList.add('open')},300)};
        document.addEventListener('click',e=>{if(!inp.contains(e.target)&&!dd.contains(e.target))dd.classList.remove('open')});
    }

    // ─── FEED ─────────────────────────────────────────────────
    createPostBox(){
        return '<div class="create-post-box" id="createPostBox"><div class="cp-row">'+this.avatarHtml(this.me.avatar,44)+'<textarea class="cp-textarea" id="cpText" placeholder="'+t('write_post')+'" rows="2"></textarea></div><div id="cpMediaPreview"></div><div class="cp-actions"><button class="cp-btn" onclick="document.getElementById(\'cpFile\').click()">📷</button><input type="file" id="cpFile" accept="image/*,video/*" style="display:none"><button class="cp-submit" id="cpSubmit">📝 '+t('create_post')+'</button></div></div>';
    }

    setupCreatePost(){
        let mediaUrl=null,mediaType=null;
        const fi=document.getElementById('cpFile');
        if(fi)fi.onchange=async e=>{const f=e.target.files[0];if(!f)return;const fd=new FormData();fd.append('media',f);const r=await fetch('/api/media',{method:'POST',body:fd});const d=await r.json();if(d.success){mediaUrl=d.url;mediaType=d.type;document.getElementById('cpMediaPreview').innerHTML='<div class="cp-media-preview">'+(d.type==='image'?'<img src="'+d.url+'">':'<video src="'+d.url+'" controls>')+'<button class="cp-remove-media" onclick="document.getElementById(\'cpMediaPreview\').innerHTML=\'\'">✕</button></div>'}};
        const sub=document.getElementById('cpSubmit');
        if(sub)sub.onclick=async()=>{const content=document.getElementById('cpText').value.trim();if(!content&&!mediaUrl)return;sub.disabled=true;
            const r=await fetch('/api/posts',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({content,media_url:mediaUrl,media_type:mediaType})});
            const post=await r.json();sub.disabled=false;document.getElementById('cpText').value='';document.getElementById('cpMediaPreview').innerHTML='';mediaUrl=null;
            const list=document.getElementById('feedList');if(list)list.insertAdjacentHTML('afterbegin',this.postCard(post))};
    }

    async loadFeed(){
        const list=document.getElementById('feedList');if(!list)return;
        const r=await fetch('/api/feed?page='+this.feedPage);const d=await r.json();
        if(!d.posts?.length&&this.feedPage===1){list.innerHTML='<div class="empty-state"><div class="es-icon">📭</div><h3>'+t('no_posts')+'</h3><p>Подпишитесь на кого-нибудь</p></div>';return}
        d.posts.forEach(p=>list.insertAdjacentHTML('beforeend',this.postCard(p)));
        if(d.has_more)list.insertAdjacentHTML('beforeend','<button class="load-more-btn" onclick="app.feedPage++;app.loadFeed()">Загрузить ещё</button>');
    }

    postCard(p){
        if(!p||p.is_deleted)return'';
        const a=p.author||{};const ava=this.avatarHtml(a.avatar,44);const nft=a.nft_badge?'<span class="nft-badge" style="font-size:14px">'+a.nft_badge.emoji+'</span>':'';
        const liked=p.is_liked?'liked':'';
        let media='';if(p.media_url){if(p.media_type==='image')media='<img src="'+p.media_url+'" class="post-media" loading="lazy">';else if(p.media_type==='video')media='<video src="'+p.media_url+'" class="post-media-video" controls></video>'}
        const text=p.content?'<div class="post-content">'+this.renderText(p.content)+'</div>':'';
        return '<div class="post-card" data-post-id="'+p.id+'"><div class="post-header"><a class="post-avatar" href="/profile/'+(a.username||'')+'">'+ava+'</a><div class="post-meta"><a class="post-author" href="/profile/'+(a.username||'')+'">'+this.esc(a.display_name||'')+nft+'</a><div class="post-time">'+this.fmtTime(p.created_at)+'</div></div>'+(a.username===this.me.username?'<div class="post-options" onclick="app.postMenu(event,'+p.id+')">⋯</div>':'')+'</div>'+text+media+'<div class="post-actions"><button class="pa-btn '+liked+'" onclick="app.likePost('+p.id+',this)"><svg width="18" height="18" viewBox="0 0 24 24" fill="'+(p.is_liked?'currentColor':'none')+'" stroke="currentColor" stroke-width="2"><path d="M20.84 4.61a5.5 5.5 0 00-7.78 0L12 5.67l-1.06-1.06a5.5 5.5 0 00-7.78 7.78l1.06 1.06L12 21.23l7.78-7.78 1.06-1.06a5.5 5.5 0 000-7.78z"/></svg><span class="pa-count like-count">'+(p.likes_count||0)+'</span></button><button class="pa-btn" onclick="app.toggleComments('+p.id+')"><svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 15a2 2 0 01-2 2H7l-4 4V5a2 2 0 012-2h14a2 2 0 012 2z"/></svg><span class="pa-count">'+(p.comments_count||0)+'</span></button><span class="pa-spacer"></span><button class="pa-btn" onclick="navigator.clipboard.writeText(location.origin+\'/post/'+p.id+'\');app.showToast(\''+t('copied')+'\')"><svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="18" cy="5" r="3"/><circle cx="6" cy="12" r="3"/><circle cx="18" cy="19" r="3"/><line x1="8.59" y1="13.51" x2="15.42" y2="17.49"/><line x1="15.41" y1="6.51" x2="8.59" y2="10.49"/></svg></button></div><div id="comments_'+p.id+'"></div></div>';
    }

    async likePost(pid,btn){const r=await fetch('/api/posts/'+pid+'/like',{method:'POST'});const d=await r.json();btn.classList.toggle('liked',d.liked);const svg=btn.querySelector('svg');if(svg)svg.setAttribute('fill',d.liked?'currentColor':'none');const cnt=btn.querySelector('.like-count');if(cnt)cnt.textContent=d.likes_count}

    async toggleComments(pid){const sec=document.getElementById('comments_'+pid);if(!sec)return;if(sec.querySelector('.comment-input-row')){sec.innerHTML='';return}
        const r=await fetch('/api/posts/'+pid+'/comments');const comments=await r.json();
        sec.innerHTML='<div class="comments-section"><div class="comment-input-row">'+this.avatarHtml(this.me.avatar,36)+'<input class="comment-input" id="ci_'+pid+'" placeholder="Комментарий..." onkeydown="if(event.key===\'Enter\')app.addComment('+pid+')"><button class="comment-send" onclick="app.addComment('+pid+')">↑</button></div><div id="clist_'+pid+'">'+comments.map(c=>'<div class="comment-item">'+this.avatarHtml(c.author?.avatar,36)+'<div class="comment-bubble"><div class="comment-name"><a href="/profile/'+(c.author?.username||'')+'">'+this.esc(c.author?.display_name||'')+'</a></div><div class="comment-text">'+this.esc(c.content)+'</div><div class="comment-time">'+this.fmtTime(c.created_at)+'</div></div></div>').join('')+'</div></div>'}

    async addComment(pid){const inp=document.getElementById('ci_'+pid);if(!inp||!inp.value.trim())return;const r=await fetch('/api/posts/'+pid+'/comments',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({content:inp.value.trim()})});const c=await r.json();inp.value='';const list=document.getElementById('clist_'+pid);if(list)list.insertAdjacentHTML('beforeend','<div class="comment-item">'+this.avatarHtml(c.author?.avatar,36)+'<div class="comment-bubble"><div class="comment-name">'+this.esc(c.author?.display_name||'')+'</div><div class="comment-text">'+this.esc(c.content)+'</div></div></div>')}

    postMenu(e,pid){e.stopPropagation();const ctx=document.getElementById('ctxMenu');ctx.innerHTML='<div class="ctx-item" onclick="app.deletePost('+pid+')">🗑️ '+t('delete')+'</div>';ctx.style.display='block';ctx.style.left=Math.min(e.clientX,innerWidth-180)+'px';ctx.style.top=e.clientY+'px'}
    async deletePost(pid){if(!confirm('Удалить?'))return;await fetch('/api/posts/'+pid,{method:'DELETE'});document.querySelector('[data-post-id="'+pid+'"]')?.remove();document.getElementById('ctxMenu').style.display='none'}

    async renderPostPage(pid){const c=document.getElementById('pageContent');const r=await fetch('/api/posts/'+pid);const p=await r.json();if(p.error){c.innerHTML='<div class="empty-state"><h3>Пост не найден</h3></div>';return}c.innerHTML=this.postCard(p);this.toggleComments(pid)}

    // ─── STORIES ──────────────────────────────────────────────
    async loadStories(){
        const sb=document.getElementById('storiesBar');const list=document.getElementById('storiesList');
        if(!sb||!list)return;
        const r=await fetch('/api/stories');const groups=await r.json();
        if(!groups.length){sb.style.display='none';return}
        sb.style.display='';
        let html='<div class="story-add" onclick="app.addStory()"><div class="story-add-icon">+</div><span>История</span></div>';
        groups.forEach(g=>{const u=g.user;const ava=u.avatar?.startsWith('emoji:')?u.avatar.substring(6):'<img src="/avatars/'+(u.avatar||'default.png')+'" style="width:100%;height:100%;object-fit:cover;border-radius:50%">';
            html+='<div class="story-item"><div class="story-ring '+(g.has_unseen?'':'seen')+'"><div class="story-avatar">'+ava+'</div></div><span>'+this.esc((u.display_name||'').substring(0,10))+'</span></div>'});
        list.innerHTML=html;
    }

    addStory(){const inp=document.createElement('input');inp.type='file';inp.accept='image/*,video/*';inp.onchange=async e=>{const f=e.target.files[0];if(!f)return;const fd=new FormData();fd.append('media',f);fd.append('text','');fd.append('bg','#000');await fetch('/api/stories',{method:'POST',body:fd});this.showToast('✅ История добавлена');this.loadStories()};inp.click()}

    // ─── MESSAGES ─────────────────────────────────────────────
    messagesHTML(){
        return '<div class="messages-layout"><div class="chat-list-panel"><div class="clp-header"><h3>'+t('messages')+'</h3><div style="display:flex;gap:6px"><button class="btn-sm btn-secondary" onclick="app.openNewDM()">+'+t('new_chat')+'</button></div></div><div class="clp-search"><input type="text" placeholder="Поиск..." id="chatSearch" oninput="app.filterChats(this.value)"></div><div class="chat-items" id="chatItems"></div></div><div class="chat-view-panel" id="chatViewPanel"><div class="no-chat"><div class="big-logo">💬</div><h3>'+t('messages')+'</h3><p>Выберите чат</p></div></div></div>';
    }

    async loadChats(){
        const r=await fetch('/api/chats');this.chats=await r.json();this.renderChatList();
        for(const c of this.chats)this.socket.emit('join_chat',{chat_id:c.id});
    }

    renderChatList(filter){
        const el=document.getElementById('chatItems');if(!el)return;
        let chats=filter?this.chats.filter(c=>(c.name||'').toLowerCase().includes(filter.toLowerCase())):this.chats;
        if(!chats.length){el.innerHTML='<div style="text-align:center;padding:40px;color:var(--text2)">'+t('no_chats')+'</div>';return}
        el.innerHTML=chats.map(c=>{const name=c.name||'Chat';const ava=this.avatarHtml(c.other_user?.avatar||c.avatar,48);const online=c.other_user?.is_online;const lm=c.last_message;const preview=lm?(lm.sender_name+': '+this.trunc(lm.content,25)):'';const time=lm?this.fmtTime(lm.created_at):'';
            return '<div class="chat-item '+(c.id===this.currentChatId?'active':'')+'" onclick="app.openChat('+c.id+')"><div class="chat-item-avatar">'+ava+(online?'<div class="chat-online-dot"></div>':'')+'</div><div class="chat-item-info"><div class="chat-item-top"><span class="chat-item-name">'+this.esc(name)+'</span><span class="chat-item-time">'+time+'</span></div><div class="chat-item-preview">'+this.esc(preview)+(c.unread_count>0?'<span class="chat-unread">'+c.unread_count+'</span>':'')+'</div></div></div>'}).join('');
    }

    filterChats(q){this.renderChatList(q)}

    async openChat(cid){
        this.currentChatId=cid;
        const chat=this.chats.find(c=>c.id===cid);if(!chat)return;
        this.replyingTo=null;this.editingMsgId=null;
        const panel=document.getElementById('chatViewPanel');if(!panel)return;
        const name=chat.name||'Chat';const ava=this.avatarHtml(chat.other_user?.avatar||chat.avatar,40);const online=chat.other_user?.is_online;
        panel.innerHTML='<div class="cvp-header"><div class="cvp-avatar">'+ava+'</div><div class="cvp-info"><h4>'+this.esc(name)+'</h4><div class="cvp-status '+(online?'online':'')+'" id="cvpStatus">'+(online?t('online'):'')+'</div></div></div><div class="messages-list" id="msgList"></div><div class="msg-input-area" id="msgInputArea"><div class="msg-input-row"><button class="msg-btn" onclick="document.getElementById(\'msgFile\').click()">📎</button><input type="file" id="msgFile" style="display:none" onchange="app.sendMediaMsg(this)"><textarea class="msg-input" id="msgInput" placeholder="Сообщение..." rows="1" onkeydown="if(event.key===\'Enter\'&&!event.shiftKey){event.preventDefault();app.sendMsg()}" oninput="app.emitTyping()"></textarea><button class="msg-send" onclick="app.sendMsg()"><svg viewBox="0 0 24 24" width="18" height="18" fill="currentColor"><path d="M2.01 21L23 12 2.01 3 2 10l15 2-15 2z"/></svg></button></div></div>';

        const r=await fetch('/api/chats/'+cid+'/messages');const d=await r.json();
        const list=document.getElementById('msgList');if(!list)return;
        list.innerHTML=d.messages.map(m=>this.msgEl(m)).join('');
        list.scrollTop=list.scrollHeight;
        this.renderChatList();
        const unread=d.messages.filter(m=>m.sender_id!==this.me.id&&!m.read_by.some(r=>r.user_id===this.me.id)).map(m=>m.id);
        if(unread.length)this.socket.emit('mark_read',{chat_id:cid,message_ids:unread});
        this.socket.emit('join_chat',{chat_id:cid});
        document.getElementById('msgInput')?.focus();
    }

    msgEl(m){
        const own=m.sender_id===this.me.id;
        const ava=this.avatarHtml(m.sender_avatar,30);
        const myAva=this.avatarHtml(this.me.avatar,30);
        const checks=own?'<span class="read-checks '+(m.read_by.filter(r=>r.user_id!==this.me.id).length>0?'read':'sent')+'">'+(m.read_by.filter(r=>r.user_id!==this.me.id).length>0?'✓✓':'✓')+'</span>':'';
        let content='';
        if(m.is_deleted)content='<div class="msg-text" style="opacity:.5;font-style:italic">'+t('deleted')+'</div>';
        else if(m.message_type==='sticker')content='<div class="msg-sticker">'+m.content+'</div>';
        else if(m.media_url){if(m.media_type==='image')content='<img src="'+m.media_url+'" class="msg-media">';else content='<a href="'+m.media_url+'" target="_blank">📎</a>';if(m.content)content+='<div class="msg-text">'+this.esc(m.content)+'</div>'}
        else if(m.voice_url)content='<div class="voice-msg"><button class="voice-play" onclick="const a=this.nextElementSibling;a.paused?a.play():a.pause();this.textContent=a.paused?\'▶️\':\'⏸️\'">▶️</button><audio src="'+m.voice_url+'" preload="metadata"></audio></div>';
        else content='<div class="msg-text">'+this.renderText(m.content)+'</div>';
        const replyH=m.reply_to?'<div class="reply-preview"><div class="rp-name">'+this.esc(m.reply_to.sender_name)+'</div><div class="rp-text">'+this.esc(m.reply_to.content)+'</div></div>':'';
        const fwdH=m.forwarded_from_name?'<div class="fwd-label">↗️ '+this.esc(m.forwarded_from_name)+'</div>':'';
        const editM=m.edited_at?'<span style="font-size:10px;color:var(--text3)">('+t('edited')+')</span>':'';
        const rxns=m.reactions?.length?'<div class="msg-reactions">'+m.reactions.map(r=>'<span class="rxn-badge '+(r.users.includes(this.me.id)?'own':'')+'" onclick="app.toggleRxn('+m.id+',\''+r.emoji+'\')">'+r.emoji+' '+r.count+'</span>').join('')+'</div>':'';
        return '<div class="message '+(own?'own':'other')+'" data-msg-id="'+m.id+'" oncontextmenu="app.msgCtx(event,'+m.id+','+own+')">'+(own?'':'<div class="msg-avatar">'+ava+'</div>')+'<div><div class="'+(own?'msg-bubble-own':'msg-bubble-other')+'">'+fwdH+replyH+content+'<div class="msg-meta">'+editM+'<span class="msg-time">'+this.fmtMsgTime(m.created_at)+'</span>'+checks+'</div></div>'+rxns+'</div>'+(own?'<div class="msg-avatar">'+myAva+'</div>':'')+'</div>';
    }

    msgCtx(e,mid,own){
        e.preventDefault();const ctx=document.getElementById('ctxMenu');
        let items='<div class="ctx-item" onclick="app.replyToMsg('+mid+')">↩️ '+t('reply')+'</div>';
        items+='<div class="ctx-item" onclick="app.reactMenu('+mid+')">😊 Реакция</div>';
        if(own)items+='<div class="ctx-item danger" onclick="app.deleteMsg('+mid+')">🗑️ '+t('delete')+'</div>';
        ctx.innerHTML=items;ctx.style.display='block';ctx.style.left=Math.min(e.clientX,innerWidth-180)+'px';ctx.style.top=Math.min(e.clientY,innerHeight-150)+'px';
    }

    replyToMsg(mid){document.getElementById('ctxMenu').style.display='none';this.replyingTo=mid;const area=document.getElementById('msgInputArea');if(!area)return;let rb=document.getElementById('replyBar');if(rb)rb.remove();rb=document.createElement('div');rb.id='replyBar';rb.className='reply-bar';rb.innerHTML='<div class="reply-bar-info"><div class="reply-bar-name">↩️ '+t('reply')+'</div></div><button class="reply-bar-close" onclick="app.cancelReply()">✕</button>';area.insertBefore(rb,area.firstChild);document.getElementById('msgInput')?.focus()}
    cancelReply(){this.replyingTo=null;document.getElementById('replyBar')?.remove()}

    reactMenu(mid){document.getElementById('ctxMenu').style.display='none';const emojis=['👍','❤️','😂','😮','😢','🔥','👏','🎉'];const ctx=document.getElementById('ctxMenu');ctx.innerHTML=emojis.map(e=>'<div class="ctx-item" onclick="app.toggleRxn('+mid+',\''+e+'\')">'+e+'</div>').join('');ctx.style.display='block'}
    toggleRxn(mid,emoji){this.socket.emit('add_reaction',{message_id:mid,emoji});document.getElementById('ctxMenu').style.display='none'}

    onReaction(d){if(d.chat_id!==this.currentChatId)return;const el=document.querySelector('[data-msg-id="'+d.message_id+'"]');if(!el)return;let rc=el.querySelector('.msg-reactions');if(!rc){rc=document.createElement('div');rc.className='msg-reactions';el.querySelector('.msg-bubble-own,.msg-bubble-other')?.parentElement?.appendChild(rc)}rc.innerHTML=d.reactions.map(r=>'<span class="rxn-badge '+(r.users.includes(this.me.id)?'own':'')+'" onclick="app.toggleRxn('+d.message_id+',\''+r.emoji+'\')">'+r.emoji+' '+r.count+'</span>').join('')}

    deleteMsg(mid){document.getElementById('ctxMenu').style.display='none';this.socket.emit('delete_message',{message_id:mid,chat_id:this.currentChatId})}

    sendMsg(){const inp=document.getElementById('msgInput');if(!inp||!inp.value.trim())return;
        const d={chat_id:this.currentChatId,content:inp.value.trim(),type:'text'};
        if(this.replyingTo){d.reply_to_id=this.replyingTo;this.cancelReply()}
        this.socket.emit('send_message',d);inp.value='';inp.style.height='auto';
        this.socket.emit('stop_typing',{chat_id:this.currentChatId})}

    emitTyping(){if(!this.currentChatId)return;this.socket.emit('typing',{chat_id:this.currentChatId});if(this.typingTimeout)clearTimeout(this.typingTimeout);this.typingTimeout=setTimeout(()=>this.socket.emit('stop_typing',{chat_id:this.currentChatId}),2000)}

    async sendMediaMsg(inp){const f=inp.files[0];if(!f)return;const fd=new FormData();fd.append('media',f);const r=await fetch('/api/media',{method:'POST',body:fd});const d=await r.json();if(d.success)this.socket.emit('send_message',{chat_id:this.currentChatId,content:f.name,media_url:d.url,media_type_hint:d.type,type:d.type});inp.value=''}

    onNewMessage(m){if(m.chat_id===this.currentChatId){const list=document.getElementById('msgList');if(list){list.insertAdjacentHTML('beforeend',this.msgEl(m));list.scrollTop=list.scrollHeight}if(m.sender_id!==this.me.id)this.socket.emit('mark_read',{chat_id:m.chat_id,message_ids:[m.id]});document.getElementById('typingInd')?.remove()}this.loadChats()}

    openNewDM(){const q=prompt('Введите юзернейм:');if(!q)return;fetch('/api/users/search?q='+encodeURIComponent(q)).then(r=>r.json()).then(users=>{if(users.length){this.startDM(users[0].id)}else this.showToast('Не найден')})}
    async startDM(uid){const r=await fetch('/api/chats/dm',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({user_id:uid})});const chat=await r.json();await this.loadChats();this.openChat(chat.id)}

    // ─── NOTIFICATIONS ────────────────────────────────────────
    async loadNotifications(){
        const r=await fetch('/api/notifications');const notifs=await r.json();fetch('/api/notifications/read',{method:'POST'});
        const el=document.getElementById('notifList');if(!el)return;
        if(!notifs.length){el.innerHTML='<div class="empty-state"><div class="es-icon">🔔</div><h3>Нет уведомлений</h3></div>';return}
        el.innerHTML=notifs.map(n=>{const u=n.from_user;const ava=u?this.avatarHtml(u.avatar,44):'';const icons={like:'❤️',comment:'💬',follow:'👤',repost:'🔁',message:'✉️'};
            return '<a class="notif-item '+(n.is_read?'':'unread')+'" href="'+(n.link||'#')+'">'+ava+'<div class="notif-text"><strong>'+this.esc(u?.display_name||'')+'</strong> '+this.esc(n.text||'')+'<div class="notif-time">'+this.fmtTime(n.created_at)+'</div></div><div class="notif-icon">'+(icons[n.type]||'🔔')+'</div></a>'}).join('')}

    async updateBadges(){const r=await fetch('/api/notifications/count');const d=await r.json();const c=d.count||0;
        ['notifBadge','slNotifBadge'].forEach(id=>{const el=document.getElementById(id);if(el){el.style.display=c>0?'flex':'none';el.textContent=c}});
        document.title=c>0?'('+c+') Gyert':'Gyert'}

    // ─── PROFILE ──────────────────────────────────────────────
    async renderProfile(username){
        const c=document.getElementById('pageContent');
        const r=await fetch('/api/users/'+username);if(!r.ok){c.innerHTML='<div class="empty-state"><h3>Не найден</h3></div>';return}
        const u=await r.json();const isMe=u.id===this.me.id;
        const nft=u.nft_badge?'<span class="nft-badge">'+u.nft_badge.emoji+'</span>':'';
        const bigAva=u.avatar?.startsWith('emoji:')?'<div style="font-size:48px">'+u.avatar.substring(6)+'</div>':'<img src="/avatars/'+(u.avatar||'default.png')+'" style="width:100%;height:100%;object-fit:cover">';
        const coverHtml=u.cover_image?'<img src="'+u.cover_image+'" style="width:100%;height:100%;object-fit:cover">':'';
        let actionBtns=isMe?'<a class="btn-primary" href="/feed" onclick="app.openEditProfile();return false">'+t('edit_profile')+'</a>':'<button class="btn-primary" id="followBtn_'+u.id+'" onclick="app.toggleFollow('+u.id+')">'+(u.is_following?t('unfollow'):t('follow'))+'</button><button class="btn-secondary" onclick="app.startDM('+u.id+')">💬</button>';
        c.innerHTML='<div class="profile-page"><div class="profile-cover">'+coverHtml+'</div><div class="profile-info-row"><div class="profile-avatar-wrap"><div class="profile-big-avatar">'+bigAva+'</div></div><div class="profile-name-row"><span class="profile-name">'+this.esc(u.display_name||'')+nft+'</span><span class="profile-username">@'+this.esc(u.username)+'</span></div>'+(u.bio?'<div class="profile-bio">'+this.renderText(u.bio)+'</div>':'')+'<div class="profile-stats"><div class="pstat"><strong>'+(u.followers_count||0)+'</strong><span>'+t('followers')+'</span></div><div class="pstat"><strong>'+(u.following_count||0)+'</strong><span>'+t('following')+'</span></div><div class="pstat"><strong>'+(u.posts_count||0)+'</strong><span>'+t('posts')+'</span></div></div><div class="profile-actions">'+actionBtns+'</div></div><div id="profilePosts" style="margin-top:16px"></div></div>';
        const pr=await fetch('/api/users/'+username+'/posts');const pd=await pr.json();
        const pp=document.getElementById('profilePosts');if(pp)pd.posts?.forEach(post=>pp.insertAdjacentHTML('beforeend',this.postCard(post)));
    }

    async toggleFollow(uid){const r=await fetch('/api/users/'+uid+'/follow',{method:'POST'});const d=await r.json();const btn=document.getElementById('followBtn_'+uid);if(btn){btn.textContent=d.following?t('unfollow'):t('follow')}}

    openEditProfile(){
        const u=this.me;
        this.openModal('<div class="modal-header"><h2>'+t('edit_profile')+'</h2><button class="modal-close" onclick="app.closeModal()">✕</button></div><div class="modal-body"><div class="field"><label>'+t('display_name')+'</label><input type="text" id="ep_name" value="'+this.esc(u.display_name||'')+'"></div><div class="field"><label>О себе</label><textarea id="ep_bio" rows="3">'+this.esc(u.bio||'')+'</textarea></div><div class="field"><label>Город</label><input type="text" id="ep_loc" value="'+this.esc(u.location||'')+'"></div><div class="field"><label>Сайт</label><input type="url" id="ep_web" value="'+this.esc(u.website||'')+'"></div></div><div class="modal-footer"><button class="btn-primary" onclick="app.saveProfile()">'+t('save')+'</button></div>');
    }

    async saveProfile(){const d={display_name:document.getElementById('ep_name')?.value,bio:document.getElementById('ep_bio')?.value,location:document.getElementById('ep_loc')?.value,website:document.getElementById('ep_web')?.value};const r=await fetch('/api/settings',{method:'PUT',headers:{'Content-Type':'application/json'},body:JSON.stringify(d)});const res=await r.json();if(res.success){this.me=res.user;this.updateNavAvatar();this.renderSidebar();this.closeModal();this.showToast('✅')}}

    // ─── SEARCH ───────────────────────────────────────────────
    async searchPage(q){if(q.length<2){document.getElementById('searchPageResults').innerHTML='';return}const r=await fetch('/api/users/search?q='+encodeURIComponent(q));const users=await r.json();const el=document.getElementById('searchPageResults');if(!el)return;el.innerHTML=users.map(u=>'<a class="search-user-item" href="/profile/'+u.username+'">'+this.avatarHtml(u.avatar,44)+'<div style="flex:1"><div style="font-weight:700">'+this.esc(u.display_name)+'</div><div style="color:var(--acc);font-size:13px">@'+this.esc(u.username)+'</div></div></a>').join('')}

    // ─── REELS ────────────────────────────────────────────────
    async loadReels(){const c=document.getElementById('reelsContainer');if(!c)return;const r=await fetch('/api/reels/all');const d=await r.json();if(!d.posts?.length){c.innerHTML='<div class="empty-state"><div class="es-icon">🎬</div><h3>Нет контента</h3><p>Создайте пост с фото или видео!</p></div>';return}c.innerHTML=d.posts.map(p=>{const a=p.author||{};const text=p.content?'<p style="color:#fff;font-size:15px;text-shadow:0 1px 4px rgba(0,0,0,.5);max-height:100px;overflow:hidden">'+this.esc(p.content.substring(0,200))+'</p>':'';let media='';if(p.media_url){if(p.media_type==='video')media='<video class="reel-video" src="'+p.media_url+'" loop playsinline muted onclick="this.paused?this.play():this.pause()"></video>';else media='<img class="reel-image" src="'+p.media_url+'" loading="lazy">'}return'<div class="reel-card">'+media+'<div class="reel-overlay"><div class="reel-content">'+text+'</div><div class="reel-sidebar"><div class="reel-action" onclick="app.likePost('+p.id+',this)"><div class="reel-action-icon '+(p.is_liked?'liked':'')+'">❤️</div><span class="like-count">'+(p.likes_count||0)+'</span></div><div class="reel-action" onclick="navigator.clipboard.writeText(location.origin+\'/post/'+p.id+'\');app.showToast(\'Copied!\')"><div class="reel-action-icon">↗️</div></div></div><a class="reel-author" href="/profile/'+(a.username||'')+'">'+this.avatarHtml(a.avatar,40)+'<div class="reel-author-info"><strong>'+this.esc(a.display_name||'')+'</strong><span>@'+this.esc(a.username||'')+'</span></div></a></div></div>'}).join('');
        // Auto play videos in view
        const obs=new IntersectionObserver(entries=>{entries.forEach(entry=>{const v=entry.target.querySelector('.reel-video');if(v){if(entry.isIntersecting)v.play().catch(()=>{});else v.pause()}})},{threshold:.5});c.querySelectorAll('.reel-card').forEach(card=>obs.observe(card))}

    // ─── AI ───────────────────────────────────────────────────
    renderAIPage(){return'<div class="ai-page"><div class="ai-header"><div class="ai-logo" style="font-size:56px;animation:float 3s ease-in-out infinite">🤖</div><h2 style="font-size:24px;background:var(--grad);-webkit-background-clip:text;-webkit-text-fill-color:transparent">GyertAI</h2><p style="color:var(--text2)">Умный помощник</p></div><div class="ai-chat" id="aiChat" style="flex:1;overflow-y:auto;padding:16px;background:var(--card);border:1px solid var(--border);border-radius:20px;margin:12px 0;display:flex;flex-direction:column;gap:12px"><div class="ai-msg ai-bot" style="display:flex;gap:10px;max-width:85%"><div style="font-size:24px">🤖</div><div style="padding:12px 16px;background:var(--bg4);border:1px solid var(--border);border-radius:18px;font-size:14px;line-height:1.6">Привет! Я GyertAI. Скоро я смогу отвечать на любые вопросы!</div></div></div><div style="display:flex;gap:10px"><input type="text" class="ai-input" id="aiInput" placeholder="Спросите..." style="flex:1;padding:12px 18px;background:var(--bg4);border:1px solid var(--border);border-radius:24px;color:var(--text);font-size:15px;outline:none" onkeydown="if(event.key===\'Enter\')app.sendAI()"><button class="msg-send" onclick="app.sendAI()">→</button></div><p style="text-align:center;font-size:12px;color:var(--text3);margin-top:8px">⚠️ AI в разработке</p></div>'}

    sendAI(){const inp=document.getElementById('aiInput');const chat=document.getElementById('aiChat');if(!inp||!chat)return;const q=inp.value.trim();if(!q)return;inp.value='';chat.innerHTML+='<div style="display:flex;gap:10px;max-width:85%;align-self:flex-end;flex-direction:row-reverse"><div style="font-size:16px">'+this.avatarHtml(this.me.avatar,32)+'</div><div style="padding:12px 16px;background:linear-gradient(135deg,rgba(77,124,255,.2),rgba(255,59,111,.12));border:1px solid rgba(77,124,255,.15);border-radius:18px;font-size:14px">'+this.esc(q)+'</div></div>';chat.scrollTop=chat.scrollHeight;setTimeout(()=>{const responses=['Интересный вопрос! AI скоро заработает на полную.','GyertAI в разработке — скоро подключим ChatGPT!','Хороший вопрос! Полноценные ответы будут после подключения API.'];chat.innerHTML+='<div style="display:flex;gap:10px;max-width:85%"><div style="font-size:24px">🤖</div><div style="padding:12px 16px;background:var(--bg4);border:1px solid var(--border);border-radius:18px;font-size:14px;line-height:1.6">'+responses[Math.floor(Math.random()*responses.length)]+'</div></div>';chat.scrollTop=chat.scrollHeight},1200)}

    // ─── RECOMMENDED ──────────────────────────────────────────
    async loadRecommended(){const el=document.getElementById('recommendedList');if(!el)return;const r=await fetch('/api/users/recommended');const users=await r.json();el.innerHTML=users.map(u=>'<div class="rec-item">'+this.avatarHtml(u.avatar,40)+'<div class="rec-info"><a class="rec-name" href="/profile/'+u.username+'">'+this.esc(u.display_name)+'</a><div class="rec-username">@'+this.esc(u.username)+'</div></div><button class="btn-follow" id="rfBtn_'+u.id+'" onclick="app.toggleFollow('+u.id+')">'+t('follow')+'</button></div>').join('')}

    // ─── NFT ──────────────────────────────────────────────────
    showNftInfo(nft){if(!nft)return;this.openModal('<div class="modal-body" style="text-align:center;padding:32px"><div style="font-size:80px;margin-bottom:16px">'+nft.emoji+'</div><h2>'+this.esc(nft.name)+'</h2><div style="font-size:24px;font-weight:800;color:var(--acc);margin:8px 0">'+this.esc(nft.price)+'</div><div style="font-size:13px;color:var(--text2)">'+this.esc(nft.index)+'</div></div>')}

    // ─── SETTINGS ─────────────────────────────────────────────
    openSettings(){document.getElementById('userMenu').classList.remove('open');this.openModal('<div class="modal-header"><h2>⚙️ '+t('settings')+'</h2><button class="modal-close" onclick="app.closeModal()">✕</button></div><div class="modal-body"><div style="margin-bottom:20px"><div style="font-size:12px;font-weight:700;color:var(--text2);text-transform:uppercase;margin-bottom:8px">'+t('theme')+'</div><div style="display:grid;grid-template-columns:repeat(2,1fr);gap:8px">'+['dark','light','midnight','ocean','office'].map(th=>'<button style="padding:10px;background:var(--bg4);border:2px solid '+(this.me.theme===th?'var(--acc)':'var(--border)')+';border-radius:10px;color:var(--text);cursor:pointer" onclick="app.applyTheme(\''+th+'\');fetch(\'/api/settings\',{method:\'PUT\',headers:{\'Content-Type\':\'application/json\'},body:JSON.stringify({theme:\''+th+'\'})})">'+t(th)+'</button>').join('')+'</div></div><div style="margin-bottom:20px"><div style="font-size:12px;font-weight:700;color:var(--text2);text-transform:uppercase;margin-bottom:8px">NFT</div><div style="display:flex;gap:8px"><input type="text" id="nftCodeInp" placeholder="'+t('nft_code')+'" style="flex:1;padding:10px;background:var(--bg4);border:1px solid var(--border);border-radius:10px;color:var(--text);outline:none"><button class="btn-primary btn-sm" onclick="app.activateNft()">'+t('activate')+'</button></div>'+(this.me.nft_badge?'<div style="margin-top:8px;font-size:13px;color:var(--text2)">Текущий: <span class="nft-badge">'+this.me.nft_badge.emoji+'</span> '+this.esc(this.me.nft_badge.name)+'</div>':'')+'</div><button class="btn-secondary" onclick="app.openEditProfile();app.closeModal()" style="width:100%;margin-bottom:8px">✏️ '+t('edit_profile')+'</button></div><div class="modal-footer"><button class="btn-danger" onclick="app.logout()">🚪 '+t('logout')+'</button></div>')}

    async activateNft(){const code=document.getElementById('nftCodeInp')?.value?.trim();if(!code)return;const r=await fetch('/api/nft/activate',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({code})});const d=await r.json();if(d.success){this.showToast('✅ NFT: '+d.nft?.nft_emoji);const mr=await fetch('/api/me');this.me=await mr.json();this.updateNavAvatar();this.renderSidebar()}else this.showToast('❌ '+(d.error||'Ошибка'))}

    // ─── THEME ────────────────────────────────────────────────
    applyTheme(th){document.body.className=document.body.className.replace(/theme-\w+/g,'')+' theme-'+th;this.me.theme=th;document.querySelectorAll('.th-btn').forEach(b=>b.classList.toggle('active',b.dataset.theme===th))}

    // ─── MODAL ────────────────────────────────────────────────
    openModal(html){document.getElementById('modalBox').innerHTML=html;document.getElementById('modalOverlay').style.display='flex';document.getElementById('modalOverlay').onclick=e=>{if(e.target===document.getElementById('modalOverlay'))this.closeModal()}}
    closeModal(){document.getElementById('modalOverlay').style.display='none'}

    // ─── UTILS ────────────────────────────────────────────────
    avatarHtml(avatar,size){size=size||44;const s='width:'+size+'px;height:'+size+'px;border-radius:50%;overflow:hidden;display:inline-flex;align-items:center;justify-content:center;background:var(--bg3);font-size:'+Math.round(size*.45)+'px;flex-shrink:0';if(!avatar||avatar==='default.png')return'<div style="'+s+'"><img src="/avatars/default.png" style="width:100%;height:100%;object-fit:cover"></div>';if(avatar.startsWith('emoji:'))return'<div style="'+s+'">'+avatar.substring(6)+'</div>';return'<div style="'+s+'"><img src="/avatars/'+avatar+'" style="width:100%;height:100%;object-fit:cover" onerror="this.outerHTML=\'😊\'"></div>'}

    renderText(text){if(!text)return'';let t=this.esc(text);t=t.replace(/\*\*(.*?)\*\*/g,'<strong>$1</strong>');t=t.replace(/\*(.*?)\*/g,'<em>$1</em>');t=t.replace(/@([a-zA-Z0-9_]+)/g,'<a href="/profile/$1" style="color:var(--acc)">@$1</a>');t=t.replace(/(https?:\/\/[^\s]+)/g,'<a href="$1" target="_blank" style="color:var(--acc)">$1</a>');return t}

    getContactName(uid,def){return(uid&&this.contactNames[uid])||def}

    toL(iso){if(!iso)return null;if(!iso.endsWith('Z')&&!iso.includes('+'))iso+='Z';return new Date(iso)}
    fmtTime(iso){const d=this.toL(iso);if(!d)return'';const n=new Date();if(n-d<86400000&&d.getDate()===n.getDate())return d.toLocaleTimeString([],{hour:'2-digit',minute:'2-digit'});if(n-d<604800000)return d.toLocaleDateString([],{weekday:'short'});return d.toLocaleDateString([],{day:'2-digit',month:'2-digit'})}
    fmtMsgTime(iso){const d=this.toL(iso);return d?d.toLocaleTimeString([],{hour:'2-digit',minute:'2-digit'}):''}
    fmtDate(iso){const d=this.toL(iso);if(!d)return'';const n=new Date();const td=new Date(n.getFullYear(),n.getMonth(),n.getDate());const md=new Date(d.getFullYear(),d.getMonth(),d.getDate());const df=td-md;if(df===0)return t('today');if(df===86400000)return t('yesterday');return d.toLocaleDateString('ru-RU',{day:'numeric',month:'long'})}
    fmtLast(iso){const d=this.toL(iso);if(!d)return'';const s=Math.floor((new Date()-d)/1000);if(s<60)return'сейчас';if(s<3600)return Math.floor(s/60)+' мин';if(s<86400)return Math.floor(s/3600)+' ч';return d.toLocaleDateString([],{day:'numeric',month:'short'})}
    trunc(s,n){return!s?'':s.length>n?s.substring(0,n)+'...':s}
    esc(t){if(!t)return'';const d=document.createElement('div');d.textContent=t;return d.innerHTML}
    showToast(msg){const el=document.getElementById('toast');el.textContent=msg;el.classList.add('show');clearTimeout(el._t);el._t=setTimeout(()=>el.classList.remove('show'),3000)}
    async logout(){await fetch('/api/logout',{method:'POST'});window.location.href='/login'}
}

window.addEventListener('DOMContentLoaded',()=>{window.app=new GyertApp()});