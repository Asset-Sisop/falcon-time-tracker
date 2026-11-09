const $ = (id) => document.getElementById(id);
const api = async (url, options={}) => {
  const response = await fetch(url, {headers:{"Content-Type":"application/json"}, ...options});
  if (!response.ok) {
    let message = `Ошибка ${response.status}`;
    try { const data = await response.json(); message = data.detail || message; } catch {}
    throw new Error(message);
  }
  return response.status === 204 ? null : response.json();
};
const fmtDuration = (seconds) => {
  if (seconds == null) return "—";
  const h=Math.floor(seconds/3600), m=Math.floor((seconds%3600)/60), s=seconds%60;
  return `${h}ч ${String(m).padStart(2,"0")}м ${String(s).padStart(2,"0")}с`;
};
const fmtDate = (value) => value ? new Date(value).toLocaleString("ru-RU",{dateStyle:"short",timeStyle:"short"}) : "—";
const toast = (message) => { $("toast").textContent=message; $("toast").classList.add("show"); setTimeout(()=>$("toast").classList.remove("show"),3200); };
let employees=[], sessions=[];
function dateDefaults(){
  const today=new Date(), week=new Date(); week.setDate(today.getDate()-6);
  $("fromDate").value=week.toISOString().slice(0,10); $("toDate").value=today.toISOString().slice(0,10);
}
async function loadEmployees(){
  employees=await api("/api/employees");
  const summary=await api("/api/summary");
  $("employeeCount").textContent=summary.employees; $("activeCount").textContent=summary.active_timers;
  $("employees").innerHTML=employees.length ? employees.map(e=>{
    const active=sessions.find(s=>s.employee_id===e.id && s.is_running);
    return `<article class="employee"><div class="employee-top"><div class="avatar">${escapeHtml(e.name.slice(0,1).toUpperCase())}</div><div><div class="employee-name">${escapeHtml(e.name)}</div><div class="employee-email">${escapeHtml(e.email||"Сотрудник")}</div></div></div>${active?`<div class="timer-active">● Таймер: ${escapeHtml(active.task)} · ${fmtDuration(Math.floor((Date.now()-new Date(active.started_at).getTime())/1000))}</div>`:""}<div class="employee-actions">${active?`<button class="primary" onclick="stopTimer(${active.id})">Остановить</button>`:`<button class="primary" onclick="openTimer(${e.id})">▶ Запустить таймер</button>`}<button class="secondary" onclick="removeEmployee(${e.id})" title="Удалить">Удалить</button></div></article>`;
  }).join("") : `<div class="empty">Пока нет сотрудников. Добавьте первого участника команды.</div>`;
}
function escapeHtml(value){return String(value).replace(/[&<>"']/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));}
async function loadSessions(){
  const params=new URLSearchParams({date_from:$("fromDate").value,date_to:$("toDate").value});
  sessions=await api(`/api/sessions?${params}`);
  $("sessionCount").textContent=sessions.length;
  $("sessionsBody").innerHTML=sessions.length?sessions.map(s=>`<tr><td>${escapeHtml(s.employee_name)}</td><td>${escapeHtml(s.task)}</td><td>${fmtDate(s.started_at)}</td><td>${fmtDate(s.stopped_at)}</td><td>${fmtDuration(s.duration_seconds ?? Math.floor((Date.now()-new Date(s.started_at).getTime())/1000))}</td><td><span class="status ${s.is_running?"running":""}">${s.is_running?"В работе":"Завершена"}</span></td></tr>`).join(""):`<tr><td colspan="6" class="empty">За выбранный период записей нет.</td></tr>`;
}
async function loadReport(){
  const params=new URLSearchParams({date_from:`${$("fromDate").value}T00:00:00`,date_to:`${$("toDate").value}T23:59:59`});
  const rows=await api(`/api/reports?${params}`);
  $("report").innerHTML=rows.length?rows.map(r=>`<article class="report-card"><span>${escapeHtml(r.employee_name)}</span><strong>${fmtDuration(r.total_seconds)}</strong><span>${r.sessions_count} сессий</span></article>`).join(""):`<div class="empty">Нет данных для отчёта.</div>`;
}
async function refresh(){await loadSessions();await loadEmployees();}
$("addEmployeeBtn").onclick=()=>$("employeeDialog").showModal();
$("employeeForm").onsubmit=async(e)=>{e.preventDefault();try{await api("/api/employees",{method:"POST",body:JSON.stringify({name:$("employeeName").value,email:$("employeeEmail").value||null})});$("employeeDialog").close();$("employeeForm").reset();await refresh();toast("Сотрудник добавлен");}catch(err){toast(err.message);}};
window.openTimer=(id)=>{$("timerEmployeeId").value=id;$("timerTitle").textContent=`Новая сессия · ${employees.find(e=>e.id===id)?.name||""}`;$("timerDialog").showModal();};
$("timerForm").onsubmit=async(e)=>{e.preventDefault();const id=$("timerEmployeeId").value;try{await api(`/api/employees/${id}/timer/start`,{method:"POST",body:JSON.stringify({task:$("taskName").value,description:$("taskDescription").value||null})});$("timerDialog").close();$("timerForm").reset();await refresh();toast("Таймер запущен");}catch(err){toast(err.message);}};
window.stopTimer=async(id)=>{try{await api(`/api/sessions/${id}/stop`,{method:"POST"});await refresh();toast("Таймер остановлен");}catch(err){toast(err.message);}};
window.removeEmployee=async(id)=>{if(!confirm("Удалить сотрудника и все его записи?"))return;try{await api(`/api/employees/${id}`,{method:"DELETE"});await refresh();toast("Сотрудник удалён");}catch(err){toast(err.message);}};
$("filterBtn").onclick=async()=>{try{await refresh();await loadReport();}catch(err){toast(err.message);}};
$("reportBtn").onclick=async()=>{try{await loadReport();toast("Отчёт обновлён");}catch(err){toast(err.message);}};
dateDefaults();
refresh().then(loadReport).catch(err=>toast(err.message));
setInterval(()=>{if(sessions.some(s=>s.is_running)){loadSessions().then(loadEmployees).catch(()=>{});}},15000);
