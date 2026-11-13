const COLORS = {Mamdani:"#0d9488", Sugeno:"#2563eb", Tsukamoto:"#16a34a"};
const $ = id => document.getElementById(id);
let MODS = {}, current = null, values = {}, timer;

async function api(path, body){
  const r = await fetch(path, body ? {method:"POST", headers:{"Content-Type":"application/json"}, body:JSON.stringify(body)} : {});
  if(!r.ok) throw new Error(r.status); return r.json();
}

async function init(){
  try{ await api("/api/health"); $("status").textContent="Backend online"; $("status").className="status ok"; }
  catch{ $("status").textContent="Backend offline - run app.py"; $("status").className="status bad"; return; }
  MODS = await api("/api/modules");
  $("cards").innerHTML = Object.values(MODS).map(m => `
    <button class="card" data-id="${m.id}"><h3>${m.name}</h3><p>${m.desc}</p>
    ${m.inputs.map(i=>`<span class="chip">${i.name}</span>`).join("")}
    <div class="meta">Output: ${m.output} · ${m.rules} rules</div></button>`).join("");
  document.querySelectorAll(".card").forEach(c => c.onclick = () => openModule(c.dataset.id));
  $("evMod").innerHTML = Object.values(MODS).map(m=>`<option value="${m.id}">${m.name}</option>`).join("");
  $("evMod").onchange = fillVars; $("evVar").onchange = drawSweep; fillVars();
}

function openModule(id){
  current = MODS[id]; values = {}; current.inputs.forEach(i => values[i.id] = i.default);
  $("workspace").hidden = false; $("wsTitle").textContent = current.name; $("outTitle").textContent = current.output + " (0-100)";
  buildSliders(); run(); $("workspace").scrollIntoView({behavior:"smooth"});
}
function buildSliders(){
  $("sliders").innerHTML = current.inputs.map(i => `<div class="slider"><label><span>${i.name}</span><b id="v_${i.id}">${values[i.id]} ${i.unit}</b></label>
    <input type="range" id="s_${i.id}" min="${i.min}" max="${i.max}" step="${(i.max-i.min)/200}" value="${values[i.id]}"></div>`).join("");
  current.inputs.forEach(i => $("s_"+i.id).oninput = e => {
    values[i.id] = +e.target.value; $("v_"+i.id).textContent = (+e.target.value).toFixed(1)+" "+i.unit;
    clearTimeout(timer); timer = setTimeout(run, 80); });
}
$("reset").onclick = () => { current.inputs.forEach(i => values[i.id] = i.default); buildSliders(); run(); };
$("closeWs").onclick = () => $("workspace").hidden = true;

async function run(){
  const d = await api("/api/evaluate", {module: Object.keys(MODS).find(k => MODS[k]===current), inputs: values});
  $("results").innerHTML = Object.entries(d.results).map(([k,v]) =>
    `<div class="res ${k===d.best?"best":""}"><span>${k}</span><b>${v}</b></div>`).join("");
  $("reason").textContent = d.reason;
  $("ruleCount").textContent = `(${d.fired_count} of ${d.total_rules} active, top ${d.fired.length} shown)`;
  $("rules").innerHTML = "<table><tr><th>IF</th><th>THEN</th><th>Strength</th></tr>" + d.fired.map(r =>
    `<tr><td>${current.inputs.map((i,n)=>`${i.name} is ${r.ants[n]}`).join(" AND ")}</td><td>${r.out}</td>
     <td>${r.w.toFixed(2)}<div class="bar" style="width:${r.w*100}%"></div></td></tr>`).join("") + "</table>";
  drawAgg(d); drawMFs(d);
}

function drawAgg(d){
  const c = $("aggChart"), g = c.getContext("2d"), W=c.width, H=c.height;
  g.clearRect(0,0,W,H); g.fillStyle = "rgba(13,148,136,.25)"; g.strokeStyle = COLORS.Mamdani;
  g.beginPath(); g.moveTo(0,H-20);
  d.aggregated.z.forEach((z,i)=>g.lineTo(z/100*W, H-20-d.aggregated.mu[i]*(H-30)));
  g.lineTo(W,H-20); g.closePath(); g.fill(); g.stroke();
  Object.entries(d.results).forEach(([k,v])=>{ g.strokeStyle=COLORS[k]; g.lineWidth=2; g.beginPath(); g.moveTo(v/100*W,5); g.lineTo(v/100*W,H-20); g.stroke(); });
  g.fillStyle="#888"; g.font="12px sans-serif"; g.fillText("0",2,H-5); g.fillText("100",W-26,H-5); g.fillText("Aggregated Mamdani output; lines mark each model's answer",W/2-170,H-5);
}

function drawMFs(d){
  $("mfCharts").innerHTML = current.inputs.map(i=>`<div class="muted">${i.name}</div><canvas id="mf_${i.id}" width="420" height="90"></canvas>`).join("");
  const cols = {Low:"#0d9488", Medium:"#2563eb", High:"#16a34a"};
  current.inputs.forEach(i=>{
    const cv=$("mf_"+i.id), g=cv.getContext("2d"), W=cv.width, H=cv.height, cu=current.curves[i.id];
    ["Low","Medium","High"].forEach(t=>{ g.strokeStyle=cols[t]; g.lineWidth=2; g.beginPath();
      cu[t].forEach((m,n)=>{ const x=n/60*W, y=H-8-m*(H-16); n?g.lineTo(x,y):g.moveTo(x,y); }); g.stroke(); });
    const px=(d.inputs[i.id]-i.min)/(i.max-i.min)*W; g.strokeStyle="#888"; g.setLineDash([4,3]);
    g.beginPath(); g.moveTo(px,0); g.lineTo(px,H); g.stroke(); g.setLineDash([]);
  });
}

// ---- Evaluation tab
function fillVars(){ const m = MODS[$("evMod").value]; $("evVar").innerHTML = m.inputs.map(i=>`<option value="${i.id}">${i.name}</option>`).join(""); drawSweep(); }
async function drawSweep(){
  const m = MODS[$("evMod").value], base = {}; m.inputs.forEach(i=>base[i.id]=i.default);
  const d = await api("/api/sweep", {module:m.id, variable:$("evVar").value, inputs:base});
  const c=$("sweepChart"), g=c.getContext("2d"), W=c.width, H=c.height, P=40; g.clearRect(0,0,W,H);
  g.strokeStyle="#99a"; g.fillStyle="#889"; g.font="12px sans-serif";
  [0,25,50,75,100].forEach(v=>{ const y=H-P-v/100*(H-2*P); g.beginPath(); g.moveTo(P,y); g.lineTo(W-10,y); g.globalAlpha=.25; g.stroke(); g.globalAlpha=1; g.fillText(v,8,y+4); });
  g.fillText(d.label, W/2-60, H-8);
  Object.entries(d.series).forEach(([k,arr])=>{ g.strokeStyle=COLORS[k]; g.lineWidth=2.5; g.beginPath();
    arr.forEach((v,n)=>{ const x=P+n/30*(W-P-10), y=H-P-v/100*(H-2*P); n?g.lineTo(x,y):g.moveTo(x,y); }); g.stroke(); });
  $("legend").innerHTML = Object.keys(COLORS).map(k=>`<span><i style="background:${COLORS[k]}"></i>${k}</span>`).join("");
}

document.querySelectorAll(".tab").forEach(t => t.onclick = () => {
  document.querySelectorAll(".tab").forEach(x=>x.classList.toggle("active", x===t));
  document.querySelectorAll(".view").forEach(v=>v.hidden = v.id!==t.dataset.view);
  if(t.dataset.view==="evaluation" && Object.keys(MODS).length) drawSweep();
});
init();
