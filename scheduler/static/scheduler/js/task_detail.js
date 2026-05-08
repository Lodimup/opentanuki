import { createStore } from 'https://esm.sh/zustand@4.5.5/vanilla';

const POLL_INTERVAL_MS = 2000;

const wrap = document.getElementById('task-runs-wrap');
const endpoint = wrap && wrap.dataset.taskRunsUrl;

const store = createStore((set, get) => ({
    isRunning: false,
    pollTimer: null,

    async tick() {
        if (!endpoint) return;
        try {
            const r = await fetch(endpoint, { credentials: 'same-origin' });
            if (!r.ok) return;
            const data = await r.json();
            applyRows(data.rows_html, data.has_runs);
            set({ isRunning: !!data.is_running });
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

function applyRows(html, hasRuns) {
    const tbody = document.getElementById('task-runs-tbody');
    if (tbody && typeof html === 'string') tbody.innerHTML = html;
    const card = document.getElementById('task-runs-card');
    const empty = document.getElementById('task-runs-empty');
    if (card) card.classList.toggle('hidden', !hasRuns);
    if (empty) empty.classList.toggle('hidden', !!hasRuns);
    if (window.lucide) window.lucide.createIcons();
}

function applyRunningState(running) {
    document.querySelectorAll('[data-task-id]').forEach(el => {
        el.dataset.running = running ? '1' : '0';
        const btn = el.querySelector('button.run-btn');
        if (btn) btn.disabled = running;
    });
}

store.subscribe((state, prev) => {
    if (state.isRunning !== prev.isRunning) applyRunningState(state.isRunning);
});

if (endpoint) store.getState().start();

document.addEventListener('visibilitychange', () => {
    if (document.hidden) store.getState().stop();
    else if (endpoint) store.getState().start();
});
