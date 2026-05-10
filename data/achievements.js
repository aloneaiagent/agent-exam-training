// Achievement System
const ACH = {
  first_q:{n:'初出茅庐',d:'完成第1道题',i:'🌱',r:'bronze',c:'growth'},
  ten_q:{n:'小试牛刀',d:'完成10道题',i:'⚔️',r:'bronze',c:'growth'},
  fifty_q:{n:'渐入佳境',d:'完成50道题',i:'🎯',r:'bronze',c:'growth'},
  hundred_q:{n:'百题斩',d:'完成100道题',i:'🗡️',r:'silver',c:'growth'},
  q150:{n:'蓄势待发',d:'完成150道题',i:'💪',r:'silver',c:'growth'},
  q250:{n:'厚积薄发',d:'完成250道题',i:'📚',r:'silver',c:'growth'},
  fivehundred_q:{n:'题库达人',d:'完成500道题',i:'👑',r:'gold',c:'growth'},
  q750:{n:'炉火纯青',d:'完成750道题',i:'🔥',r:'gold',c:'growth'},
  thousand_q:{n:'千题高手',d:'完成1000道题',i:'💎',r:'platinum',c:'growth'},
  q1500:{n:'学富五车',d:'完成1500道题',i:'📚',r:'platinum',c:'growth'},
  q1750:{n:'登峰造极',d:'完成1750道题',i:'⚡',r:'platinum',c:'growth'},
  all_q:{n:'题海征服者',d:'完成全部2091道题',i:'⚔️',r:'platinum',c:'growth'},
  acc_60:{n:'稳扎稳打',d:'50题以上且正确率60%+',i:'🛡️',r:'bronze',c:'battle'},
  acc_80:{n:'精准打击',d:'100题以上且正确率80%+',i:'🎪',r:'silver',c:'battle'},
  acc_90:{n:'百发百中',d:'200题以上且正确率90%+',i:'🏹',r:'gold',c:'battle'},
  streak_5:{n:'初露锋芒',d:'连续答对5题',i:'🔥',r:'bronze',c:'battle'},
  streak_10:{n:'势如破竹',d:'连续答对10题',i:'🔥',r:'silver',c:'battle'},
  streak_20:{n:'如有神助',d:'连续答对20题',i:'🔥',r:'gold',c:'battle'},
  sub1_done:{n:'思政达人',d:'完成科一全部885题',i:'📘',r:'gold',c:'mastery'},
  sub2_done:{n:'实务精英',d:'完成科二全部781题',i:'📙',r:'gold',c:'mastery'},
  wrong_zero:{n:'一尘不染',d:'错题本全部清零',i:'🧹',r:'silver',c:'social'},
};

const CAT = {growth:'成长',battle:'对局',mastery:'专精',social:'社交'};
const LV = [
  [1,0,'学徒'],[2,50,'练习生'],[3,120,'考生'],[4,250,'备考者'],
  [5,500,'赶考人'],[6,800,'秀才'],[7,1200,'举人'],[8,1800,'贡士'],
  [9,2600,'进士'],[10,3600,'探花'],[11,5000,'榜眼'],[12,7000,'状元'],
  [13,10000,'大学士'],[14,14000,'太傅'],[15,20000,'国士无双'],
];

function gG() {
  let p=loadProgress();
  if(!p.game) p.game={xp:0,unlocked:{},streak:0,maxStreak:0,answeredIds:[]};
  if(!p.game.unlocked) p.game.unlocked={};
  if(!p.game.answeredIds) p.game.answeredIds=[];
  return p.game;
}
function sG(g){let p=loadProgress();p.game=g;saveProgress(p);}
function cL(x){
  let lv=LV[0],i=LV.length-1;
  while(i>=0&&x<LV[i][1])i--;
  if(i<0)i=0;
  lv=LV[i];
  let ni=LV.findIndex(l=>l[1]>x);
  let nx=ni>=0?LV[ni]:null;
  let cur=x-lv[1],need=nx?nx[1]-lv[1]:1;
  return {lv:lv[0],title:lv[2],xp:x,cur,need,pct:need>0?Math.round(cur/need*100):100};
}

function syncGame() {
  let p=loadProgress(),g=gG();
  let rc=Object.keys(p.records||{}).length,ac=(g.answeredIds||[]).length;
  if(rc<=ac)return false;
  let sorted=Object.entries(p.records||{}).sort((a,b)=>(a[1].time||0)-(b[1].time||0));
  let xp=0,s=0,ms=0,ids=[],seen=new Set();
  for(let[qid,rec]of sorted){
    if(seen.has(qid))continue;seen.add(qid);ids.push(qid);
    xp+=rec.correct?10:2;
    if(rec.correct){s++;if(s>ms)ms=s;}else s=0;
  }
  g.xp=xp;g.answeredIds=ids;g.streak=s;g.maxStreak=ms;
  sG(g);return true;
}

function chkAch() {
  let p=loadProgress(),g=gG(),rec=p.records||{},an=Object.keys(rec).length;
  let co=Object.values(rec).filter(r=>r?.correct).length,ac=an>0?Math.round(co/an*100):0;
  let wr=(p.wrong||[]).length,un=g.unlocked||{},newly=[];
  let s1=indexData?.['科目一']?.['主题库']?.['_小计'];
  let s2=indexData?.['科目二']?.['主题库']?.['_小计'];
  function aqs(s){let p=loadProgress(),c=0;for(let src of getAllSources(s)){let sq=questionCache[src.file];if(!sq)continue;for(let q of sq)if(p.records[q.id])c++;}return c;}
  let ch={
    first_q:()=>an>=1,ten_q:()=>an>=10,fifty_q:()=>an>=50,
    hundred_q:()=>an>=100,q150:()=>an>=150,q250:()=>an>=250,
    fivehundred_q:()=>an>=500,q750:()=>an>=750,
    thousand_q:()=>an>=1000,q1500:()=>an>=1500,q1750:()=>an>=1750,
    all_q:()=>an>=2091,
    acc_60:()=>an>=50&&ac>=60,acc_80:()=>an>=100&&ac>=80,acc_90:()=>an>=200&&ac>=90,
    streak_5:()=>g.maxStreak>=5,streak_10:()=>g.maxStreak>=10,streak_20:()=>g.maxStreak>=20,
    sub1_done:()=>s1?aqs('科目一')>=s1['总题数']:false,
    sub2_done:()=>s2?aqs('科目二')>=s2['总题数']:false,
    wrong_zero:()=>wr===0&&an>=10,
  };
  for(let[k,fn]of Object.entries(ch)){if(!un[k]&&fn()){un[k]=Date.now();newly.push(k);}}
  if(newly.length){g.unlocked=un;sG(g);
    let a=ACH[newly[newly.length-1]];
    let el=document.getElementById('achToast');
    if(el){
      document.getElementById('achToastIcon').textContent=a.i;
      document.getElementById('achToastName').textContent=a.n;
      document.getElementById('achToastDesc').textContent=a.d;
      let r=document.getElementById('achToastRarity');
      let rr={bronze:'铜·成就',silver:'银·成就',gold:'金·成就',platinum:'铂金·成就'};
      r.textContent='✦ '+(rr[a.r]||a.r)+' ✦';
      r.className='ach-rarity ach-rarity-'+a.r;
      el.classList.add('show');
      setTimeout(()=>el.classList.remove('show'),3000);
    }
  }
}

// Aliases for index.html template
function getGameState(){return gG();}
function calcLevel(x){return cL(x);}

function goAch(){
  syncGame();chkAch();
  document.querySelectorAll('.view').forEach(v=>v.classList.remove('active'));
  let v=document.getElementById('view-achievement')||document.getElementById('view-home');
  v.innerHTML='';v.classList.add('active');
  let g=gG(),level=cL(g.xp),un=g.unlocked||{};
  let keys=Object.keys(ACH),uc=keys.filter(k=>un[k]).length;
  let tabs=['all','growth','battle','mastery','social'].map((c,i)=>'<div class="ach-tab'+(i===0?' active':'')+'" onclick="rdAch(\''+c+'\')">'+(c==='all'?'全部':CAT[c])+'</div>').join('');
  v.innerHTML='<div class="page-header"><button class="back-btn" onclick="navigate(\'#home\')">← 返回</button><div class="page-title">🏆 成就</div><div class="page-sub">'+uc+'/'+keys.length+' 已解锁</div></div><div class="ach-header"><div class="ach-level-panel"><div class="ach-level-icon">Lv.'+level.lv+'</div><div class="ach-level-num">成就等级 <span class="num">'+level.lv+'</span></div><div class="xp-bar" style="margin:10px 0 2px;height:8px;"><div class="xp-fill" style="width:'+level.pct+'%;height:8px;"></div></div><div style="display:flex;justify-content:space-between;font-size:10px;color:var(--muted);"><span>Lv.'+level.lv+'</span><span>'+level.cur+'/'+level.need+' XP</span><span>Lv.'+(level.lv+1)+'</span></div><div class="ach-rank" style="margin-top:6px;">🏅 '+uc+'/'+keys.length+' 成就</div><div class="ach-rank" style="border:none;padding-top:4px">'+level.title+' <span style="cursor:pointer;color:var(--gold);font-size:11px;" onclick="showLevelPopup()">👑</span></div></div><div class="ach-main"><div class="ach-tabs">'+tabs+'</div><div id="achGrid"></div></div></div>';
  document.title='成就 · Agent Exam Training';
  rdAch('all');
}

function showLevelPopup(){
  var html='<div style="position:fixed;top:0;left:0;right:0;bottom:0;z-index:500;background:rgba(0,0,0,.7);display:flex;align-items:center;justify-content:center;" onclick="this.remove()"><div style="background:var(--bg-panel);border:1px solid var(--border);border-radius:14px;padding:24px;max-width:420px;width:90vw;box-shadow:0 12px 60px rgba(0,0,0,.6);" onclick="event.stopPropagation()"><div style="font-size:15px;font-weight:600;color:var(--gold);margin-bottom:14px;text-align:center;">👑 称号一览</div>';
  var g=gG(),level=cL(g.xp);
  html+=LV.map(function(l){
    var isCur=l[0]===level.lv;
    var pct=isCur?level.pct:0;
    var bar=isCur?'<div class="xp-bar" style="height:3px;margin-top:4px;"><div class="xp-fill" style="width:'+pct+'%"></div></div>':'';
    return '<div style="display:flex;align-items:center;padding:8px 12px;border-radius:6px;'+(isCur?'background:rgba(230,184,74,.1);border:1px solid var(--gold-dim);':'')+';margin-bottom:4px;"><div style="width:40px;font-size:12px;color:var(--muted);">Lv.'+l[0]+'</div><div style="flex:1;font-size:14px;font-weight:'+(isCur?'700':'400')+';color:'+(isCur?'var(--gold)':'var(--white)')+';">'+l[2]+'</div><div style="font-size:11px;color:var(--muted);text-align:right;">'+l[1]+'XP</div></div>'+bar;
  }).join('');
  html+='<div style="text-align:center;margin-top:12px;"><button class="btn btn-secondary btn-small" onclick="this.closest(\'[onclick]\').remove()">关闭</button></div></div></div>';
  var d=document.createElement('div');d.innerHTML=html;
  document.body.appendChild(d.firstElementChild);
}

function rdAch(cat){
  document.querySelectorAll('.ach-tab').forEach(t=>{
    let c=t.textContent;
    t.classList.toggle('active',cat==='all'?c==='全部':c===CAT[cat]);
  });
  let g=gG(),un=g.unlocked||{},p=loadProgress(),rec=p.records||{},an=Object.keys(rec).length;
  let co=Object.values(rec).filter(r=>r?.correct).length,ac=an>0?Math.round(co/an*100):0;
  let wr=(p.wrong||[]).length;
  let s1=indexData?.['科目一']?.['主题库']?.['_小计'];
  let s2=indexData?.['科目二']?.['主题库']?.['_小计'];
  function aqs(s){let c=0;for(let src of getAllSources(s)){let sq=questionCache[src.file];if(!sq)continue;for(let q of sq)if(p.records[q.id])c++;}return c;}
  let prg={
    first_q:[an,1],ten_q:[an,10],fifty_q:[an,50],hundred_q:[an,100],
    q150:[an,150],q250:[an,250],fivehundred_q:[an,500],q750:[an,750],
    thousand_q:[an,1000],q1500:[an,1500],q1750:[an,1750],all_q:[an,2091],
    acc_60:[an>=50?Math.min(ac,60):0,60],acc_80:[an>=100?Math.min(ac,80):0,80],acc_90:[an>=200?Math.min(ac,90):0,90],
    streak_5:[Math.min(g.maxStreak,5),5],streak_10:[Math.min(g.maxStreak,10),10],streak_20:[Math.min(g.maxStreak,20),20],
    sub1_done:[aqs('科目一'),s1?s1['总题数']:0],
    sub2_done:[aqs('科目二'),s2?s2['总题数']:0],
    wrong_zero:[Math.max(0,10-wr),10],
  };
  let rar={bronze:'铜',silver:'银',gold:'金',platinum:'铂金'};
  let keys=Object.entries(ACH).filter(([k,a])=>cat==='all'||a.c===cat)
    .sort(([ka],[kb])=>((un[kb]?1:0)-(un[ka]?1:0)));
  let grid=keys.map(([k,a])=>{
    let u=!!un[k],p2=prg[k]||[0,1],pct=Math.min(100,Math.round(p2[0]/p2[1]*100));
    let ds=u?new Date(un[k]).toLocaleDateString('zh-CN',{month:'numeric',day:'numeric'}):'';
    let gc=a.r==='gold'||a.r==='platinum'?' gold':'';
    let c='<div class="ach-card'+(u?gc:' locked')+'"><div class="ac-glow"></div><div class="ac-icon">'+a.i+'</div><div class="ac-name">'+a.n+'</div><div class="ac-desc">'+a.d+'</div>';
    if(u){c+='<div class="ac-rarity ach-rarity-'+a.r+'">✦ '+(rar[a.r]||a.r)+'</div>';if(ds)c+='<div class="ac-date">'+ds+' 获得</div>';}
    else{c+='<div class="ac-progress">'+p2[0]+'/'+p2[1]+'</div><div class="ac-rarity" style="color:var(--muted)">🔒 未获得</div>';}
    c+='</div>';return c;
  }).join('');
  let el=document.getElementById('achGrid');if(el)el.innerHTML='<div class="ach-grid">'+grid+'</div>';
}
