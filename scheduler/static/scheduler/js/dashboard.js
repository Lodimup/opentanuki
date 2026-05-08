import { createStore } from 'https://esm.sh/zustand@4.5.5/vanilla';

const POLL_INTERVAL_MS = 2000;
const ENDPOINT = '/api/dashboard';

const store = createStore((set, get) => ({
    runningIds: new Set(),
    pollTimer: null,

    async tick() {
        try {
            const r = await fetch(ENDPOINT, { credentials: 'same-origin' });
            if (!r.ok) return;
            const data = await r.json();
            const ids = new Set(data.active_task_ids);
            set({ runningIds: ids });
            applyRecent(data.recent_html);
            if (ids.size === 0) get().stop();
        } catch (e) { /* ignore */ }
    },

    start() {
        if (get().pollTimer) return;
        get().tick();
        const id = setInterval(() => get().tick(), POLL_INTERVAL_MS);
        set({ pollTimer: id });
    },

    stop() {
        const id = get().pollTimer;
        if (id) clearInterval(id);
        set({ pollTimer: null });
    },
}));

function applyButtons(state) {
    const ids = state.runningIds;
    document.querySelectorAll('[data-task-id]').forEach(el => {
        const tid = el.dataset.taskId;
        const running = ids.has(tid);
        el.dataset.running = running ? '1' : '0';
        const btn = el.querySelector('button.run-btn');
        if (btn) btn.disabled = running;
    });
}

function applyRecent(html) {
    const tbody = document.getElementById('recent-runs-tbody');
    if (!tbody || typeof html !== 'string') return;
    tbody.innerHTML = html;
    if (window.lucide) window.lucide.createIcons();
}

store.subscribe((state, prev) => {
    if (state.runningIds !== prev.runningIds) applyButtons(state);
});

window.tanuki = {
    start: () => store.getState().start(),
    stop: () => store.getState().stop(),
    tick: () => store.getState().tick(),
};

const seeded = document.querySelectorAll('[data-task-id][data-running="1"]').length;
if (seeded > 0) store.getState().start();
