const API = "http://127.0.0.1:8000/api";

let currentUser = null;
let currentTicketId = null;
let refreshTimer = null;

document.addEventListener("DOMContentLoaded", () => {
    initTabs();
    checkAuth();
});


function showMessage(text, type = "ok") {
    const box = document.createElement("div");
    box.className = "notify-box " + type;
    box.innerText = text;

    const container = document.getElementById("notify");
    container.appendChild(box);

    setTimeout(() => box.remove(), 5000);
}


function initTabs() {
    const buttons = document.querySelectorAll(".tab");

    buttons.forEach(btn => {
        btn.addEventListener("click", () => {
            const tabId = btn.dataset.tab;

            activateTab(btn.id, tabId);

            if (tabId === "tab-my") loadMyTickets();
            if (tabId === "tab-open") loadOpenTickets();
            if (tabId === "tab-assigned") loadAssignedTickets();
            if (tabId === "tab-kb") loadKnowledge();
            if (tabId === "tab-stats") loadStats();
        });
    });
}


function activateTab(buttonId, tabId) {
    document.querySelectorAll(".tab").forEach(t => {
        t.classList.remove("active");
    });

    document.querySelectorAll(".tab-page").forEach(p => {
        p.classList.remove("active");
    });

    const btn = document.getElementById(buttonId);
    if (btn) btn.classList.add("active");

    const page = document.getElementById(tabId);
    if (page) page.classList.add("active");
}


function openDetailsTab() {
    document.querySelectorAll(".tab-page").forEach(p => {
        p.classList.remove("active");
    });

    document.querySelectorAll(".tab").forEach(t => {
        t.classList.remove("active");
    });

    document.getElementById("tab-details").classList.add("active");
}


function backToAssigned() {
    if (currentUser.role === "specialist") {
        activateTab("tab-assigned-btn", "tab-assigned");
        loadAssignedTickets();
    } else {
        activateTab("tab-my-btn", "tab-my");
        loadMyTickets();
    }
}


function checkAuth() {
    const userId = localStorage.getItem("user_id");
    if (userId) loadUser(userId);
}


async function loadUser(userId) {
    try {
        const r = await fetch(`${API}/users/me?user_id=${userId}`);

        if (!r.ok) {
            logout();
            return;
        }

        currentUser = await r.json();
        showUI();
    } catch (err) {
        logout();
    }
}


function stopAutoRefresh() {
    if (refreshTimer) {
        clearInterval(refreshTimer);
        refreshTimer = null;
    }
}


function startAutoRefresh() {
    stopAutoRefresh();

    if (!currentUser) return;

    if (currentUser.role === "specialist") {
        refreshTimer = setInterval(() => {
            loadOpenTickets();
            loadAssignedTickets();
        }, 5000);
    }
}


function showUI() {
    document.getElementById("login-form").classList.add("hidden");
    document.getElementById("app-ui").classList.remove("hidden");

    document.getElementById("user-box").classList.remove("hidden");
    document.getElementById("user-name").innerText = currentUser.full_name;
    document.getElementById("user-role").innerText = roleName(currentUser.role);

    hideAllTabs();

    if (currentUser.role === "user") {
        showUserTabs();
        activateTab("tab-create-btn", "tab-create");
    }

    if (currentUser.role === "specialist") {
        showSpecialistTabs();
        activateTab("tab-open-btn", "tab-open");
        loadOpenTickets();
        loadAssignedTickets();
    }

    if (currentUser.role === "admin") {
        showAdminTabs();
        activateTab("tab-kb-btn", "tab-kb");
        loadKnowledge();
    }

    startAutoRefresh();
}


function hideAllTabs() {
    const tabIds = [
        "tab-create-btn",
        "tab-my-btn",
        "tab-open-btn",
        "tab-assigned-btn",
        "tab-kb-btn",
        "tab-stats-btn"
    ];

    tabIds.forEach(id => {
        const tab = document.getElementById(id);
        if (tab) tab.classList.add("hidden");
    });
}


function showUserTabs() {
    document.getElementById("tab-create-btn").classList.remove("hidden");
    document.getElementById("tab-my-btn").classList.remove("hidden");
}


function showSpecialistTabs() {
    document.getElementById("tab-open-btn").classList.remove("hidden");
    document.getElementById("tab-assigned-btn").classList.remove("hidden");
}


function showAdminTabs() {
    document.getElementById("tab-kb-btn").classList.remove("hidden");
    document.getElementById("tab-stats-btn").classList.remove("hidden");
}


async function login(event) {
    event.preventDefault();

    const email = document.getElementById("email").value.trim();
    const password = document.getElementById("password").value.trim();

    try {
        const r = await fetch(`${API}/login`, {
            method: "POST",
            headers: {"Content-Type": "application/json"},
            body: JSON.stringify({email, password})
        });

        if (!r.ok) {
            showMessage("Неверный логин или пароль", "err");
            return;
        }

        const data = await r.json();
        localStorage.setItem("user_id", data.user_id);

        await loadUser(data.user_id);
        showMessage("Вход выполнен");
    } catch (err) {
        showMessage("Ошибка соединения с сервером", "err");
    }
}


function logout() {
    stopAutoRefresh();
    localStorage.removeItem("user_id");
    location.reload();
}


async function createTicket(event) {
    event.preventDefault();

    const description = document.getElementById("description").value;
    const contact_info = document.getElementById("contact-info").value;

    try {
        const r = await fetch(`${API}/tickets?user_id=${currentUser.id}`, {
            method: "POST",
            headers: {"Content-Type": "application/json"},
            body: JSON.stringify({description, contact_info})
        });

        if (!r.ok) {
            showMessage("Ошибка создания заявки", "err");
            return;
        }

        document.getElementById("description").value = "";
        document.getElementById("contact-info").value = "";

        showMessage("Заявка создана");
        loadMyTickets();
    } catch (err) {
        showMessage("Ошибка соединения", "err");
    }
}


async function loadMyTickets() {
    try {
        const r = await fetch(`${API}/tickets/my?user_id=${currentUser.id}`);
        if (!r.ok) return;

        const tickets = await r.json();
        renderTickets(tickets, "my-list", false, false);
    } catch (err) {
        showMessage("Ошибка загрузки заявок", "err");
    }
}


async function loadOpenTickets() {
    try {
        const r = await fetch(`${API}/tickets/open?user_id=${currentUser.id}`);
        if (!r.ok) return;

        const tickets = await r.json();
        renderTickets(tickets, "open-list", true, false);
    } catch (err) {
        showMessage("Ошибка загрузки заявок", "err");
    }
}


async function loadAssignedTickets() {
    try {
        const r = await fetch(`${API}/tickets/assigned?user_id=${currentUser.id}`);
        if (!r.ok) return;

        const tickets = await r.json();
        renderTickets(tickets, "assigned-list", false, true);
    } catch (err) {
        showMessage("Ошибка загрузки заявок", "err");
    }
}


function renderTickets(tickets, containerId, showAssign, showDetails) {
    const box = document.getElementById(containerId);
    box.innerHTML = "";

    if (!tickets || tickets.length === 0) {
        box.innerHTML = "<div>Нет заявок</div>";
        return;
    }

    tickets.forEach(t => {
        const div = document.createElement("div");
        div.className = "ticket";

        let buttons = "";

        if (showAssign) {
            buttons += `
                <button class="btn" onclick="assignTicket(${t.id})">
                    Взять
                </button>
            `;
        }

        if (showDetails) {
            buttons += `
                <button class="btn btn-light" onclick="openTicket(${t.id})">
                    Подробнее
                </button>
            `;
        }

        if (currentUser && currentUser.role === "user" && t.status_id === 3) {
            buttons += `
                <button class="btn btn-green" onclick="confirmTicket(${t.id})">
                    Подтвердить
                </button>

                <button class="btn btn-light" onclick="returnTicket(${t.id})">
                    Вернуть в работу
                </button>
            `;
        }

        div.innerHTML = `
            <div class="ticket-title">
                <b>Заявка #${t.id}</b>
                <span class="badge ${statusClass(t.status_id)}">
                    ${statusText(t.status_id)}
                </span>
            </div>

            <div><b>Описание:</b> ${t.description.substring(0, 140)}...</div>
            <div style="margin-top: 8px;"><b>Контакты:</b> ${t.contact_info}</div>

            <div style="margin-top: 12px;">
                ${buttons}
            </div>
        `;

        box.appendChild(div);
    });
}


async function confirmTicket(ticketId) {
    try {
        const r = await fetch(
            `${API}/tickets/${ticketId}/confirm?user_id=${currentUser.id}`,
            {
                method: "POST",
                headers: {"Content-Type": "application/json"},
                body: JSON.stringify({is_confirmed: true})
            }
        );

        if (!r.ok) {
            showMessage("Ошибка подтверждения заявки", "err");
            return;
        }

        showMessage("Заявка закрыта");
        loadMyTickets();
    } catch (err) {
        showMessage("Ошибка соединения", "err");
    }
}


async function returnTicket(ticketId) {
    try {
        const r = await fetch(
            `${API}/tickets/${ticketId}/return?user_id=${currentUser.id}`,
            {
                method: "POST",
                headers: {"Content-Type": "application/json"},
                body: JSON.stringify({is_confirmed: false})
            }
        );

        if (!r.ok) {
            showMessage("Ошибка возврата заявки", "err");
            return;
        }

        showMessage("Заявка возвращена в работу");
        loadMyTickets();
    } catch (err) {
        showMessage("Ошибка соединения", "err");
    }
}


async function assignTicket(ticketId) {
    try {
        const r = await fetch(
            `${API}/tickets/${ticketId}/assign?user_id=${currentUser.id}`,
            {method: "PUT"}
        );

        if (!r.ok) {
            showMessage("Ошибка назначения заявки", "err");
            return;
        }

        showMessage("Заявка взята в работу");
        loadOpenTickets();
        loadAssignedTickets();
    } catch (err) {
        showMessage("Ошибка соединения", "err");
    }
}


async function openTicket(ticketId) {
    currentTicketId = ticketId;
    openDetailsTab();

    try {
        const r = await fetch(
            `${API}/tickets/${ticketId}/recommendations?user_id=${currentUser.id}`
        );

        if (!r.ok) {
            showMessage("Ошибка получения рекомендаций", "err");
            return;
        }

        const data = await r.json();
        renderDetails(data);
    } catch (err) {
        showMessage("Ошибка соединения", "err");
    }
}


function renderDetails(data) {
    const info = document.getElementById("details-info");

    info.innerHTML = `
        <div class="details-layout">

            <div class="ticket">
                <h3>Карточка заявки</h3>

                <div><b>Описание проблемы:</b></div>
                <div style="margin-top: 6px;">
                    ${data.description}
                </div>

                <div style="margin-top: 14px;">
                    <b>Контакты клиента:</b> ${data.contact_info}
                </div>

                <div style="margin-top: 14px;">
                    <b>Статус заявки:</b>
                    <span class="badge ${statusClass(data.status_id)}">
                        ${statusText(data.status_id)}
                    </span>
                </div>

                <div style="margin-top: 14px;">
                    <b>Тип проблемы:</b> ${data.is_novel ? "Новая" : "Известная"}
                </div>
            </div>

            <div class="ticket ml-panel">
                <div class="ml-header">Интеллектуальный модуль рекомендаций</div>

                <div id="ml-recs-box"></div>
            </div>

        </div>
    `;

    const mlBox = document.getElementById("ml-recs-box");
    mlBox.innerHTML = "";

    if (!data.recommendations || data.recommendations.length === 0) {
        mlBox.innerHTML = "<div>Рекомендации отсутствуют</div>";
        return;
    }

    data.recommendations.forEach(r => {
        const div = document.createElement("div");
        div.className = "ml-recommendation";

        div.innerHTML = `
            <div><b>Рекомендация №${r.rank}</b> (${r.similarity}%)</div>

            <div style="margin-top: 8px;">
                <b>Проблема:</b> ${r.problem}
            </div>

            <div style="margin-top: 8px;">
                <b>Решение:</b> ${r.solution}
            </div>

            <button class="btn btn-green" onclick="useRec(${r.kb_id})">
                Принять рекомендацию
            </button>
        `;

        mlBox.appendChild(div);
    });
}


function useRec(kbId) {
    document.getElementById("used-kb").checked = true;
    document.getElementById("accepted-kb-id").value = kbId;
    showMessage("Рекомендация принята");
}


async function resolveTicket(event) {
    event.preventDefault();

    const used_kb = document.getElementById("used-kb").checked;
    const applied_solution = document.getElementById("applied-solution").value;

    const accepted_kb_id =
        document.getElementById("accepted-kb-id").value || null;

    if (!used_kb && applied_solution.trim().length < 5) {
        showMessage("Введите решение специалиста", "err");
        return;
    }

    try {
        const r = await fetch(
            `${API}/tickets/${currentTicketId}/resolve?user_id=${currentUser.id}`,
            {
                method: "POST",
                headers: {"Content-Type": "application/json"},
                body: JSON.stringify({
                    applied_solution,
                    used_kb,
                    accepted_kb_id
                })
            }
        );

        if (!r.ok) {
            showMessage("Ошибка завершения заявки", "err");
            return;
        }

        const data = await r.json();

        if (data.added_to_kb) {
            showMessage("Решение добавлено в базу знаний");
        } else {
            showMessage("Заявка выполнена");
        }

        document.getElementById("applied-solution").value = "";
        document.getElementById("used-kb").checked = false;
        document.getElementById("accepted-kb-id").value = "";

        backToAssigned();
    } catch (err) {
        showMessage("Ошибка соединения", "err");
    }
}


async function loadKnowledge() {
    try {
        const r = await fetch(`${API}/knowledge?user_id=${currentUser.id}&limit=200`);
        if (!r.ok) return;

        const items = await r.json();
        const box = document.getElementById("kb-list");
        box.innerHTML = "";

        if (!items || items.length === 0) {
            box.innerHTML = "<div>База знаний пуста</div>";
            return;
        }

        items.sort((a, b) => b.id - a.id);

        items.forEach(i => {
            const div = document.createElement("div");
            div.className = "ticket";

            div.innerHTML = `
                <div class="ticket-title">
                    <b>Запись #${i.id}</b>
                    <span class="badge gray">
                        Использовано: ${i.frequency}
                    </span>
                </div>

                <div><b>Проблема:</b> ${i.problem.substring(0, 160)}...</div>

                <div style="margin-top: 8px;">
                    <b>Решение:</b> ${i.solution.substring(0, 160)}...
                </div>
            `;

            box.appendChild(div);
        });
    } catch (err) {
        showMessage("Ошибка загрузки базы знаний", "err");
    }
}


async function loadStats() {
    try {
        const r = await fetch(`${API}/stats?user_id=${currentUser.id}`);
        if (!r.ok) return;

        const s = await r.json();

        document.getElementById("stats-box").innerHTML = `
            <div class="ticket">
                <div><b>Всего заявок:</b> ${s.tickets_total}</div>
                <div><b>Открытых:</b> ${s.tickets_open}</div>
                <div><b>Записей базы знаний:</b> ${s.knowledge_total}</div>
                <div><b>Использований решений:</b> ${s.knowledge_usage}</div>
            </div>
        `;
    } catch (err) {
        showMessage("Ошибка загрузки статистики", "err");
    }
}


function roleName(code) {
    if (code === "user") return "Пользователь";
    if (code === "specialist") return "Специалист";
    if (code === "admin") return "Администратор";
    return code;
}


function statusText(id) {
    if (id === 1) return "Открыта";
    if (id === 2) return "В работе";
    if (id === 3) return "Выполнена";
    if (id === 4) return "Закрыта";
    return "Неизвестно";
}


function statusClass(id) {
    if (id === 1) return "red";
    if (id === 2) return "yellow";
    if (id === 3) return "green";
    if (id === 4) return "gray";
    return "gray";
}