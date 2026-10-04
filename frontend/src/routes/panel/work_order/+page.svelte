<script lang="ts">
	import { onMount, onDestroy, tick } from 'svelte';
	import { page as pageStore } from '$app/state';
	import { api } from '$lib/api';
	import { createMap } from '$lib/fleet-map';
	import { auth } from '$lib/stores/auth.svelte';
	import { theme } from '$lib/stores/theme.svelte';

	interface WoItem {
		id: string;
		code: string;
		type: string;
		status: string;
		health: number;
		riskLevel: string;
		riskScore: number;
		rulHours: number;
		rulUncertainty: number;
		failureDate: Date;
		repairByDate: Date;
		repairDurationHours: number;
		estCompletionDate: Date;
		priority: string;
		topComponent: string;
		components: { component: string; health: number }[];
		shap: { feature: string; value: number }[];
		twins: { label: string; hours: number }[];
		estCost: number;
		woId: string;
	}

	const ATRISK = ['CRITICAL', 'WARNING', 'RUSAK'];

	let isLoading = $state(true);
	let error = $state('');
	let lastUpdate = $state('');
	let autoRefresh = $state(true);
	let woToast = $state<{ ok: boolean; msg: string } | null>(null);
	let woToastTimer: ReturnType<typeof setTimeout> | null = null;

	let items = $state<WoItem[]>([]);
	let selectedCode = $state<string | null>(null);
	let statusFilter = $state<'ALL' | 'CRITICAL' | 'WARNING' | 'RUSAK'>('ALL');

	// items table pagination
	let itemsPage = $state(1);
	const itemsPerPage = 5;
	const filteredItems = $derived(
		statusFilter === 'ALL' ? items : items.filter((it) => it.status === statusFilter)
	);
	const itemsTotalPages = $derived(Math.max(1, Math.ceil(filteredItems.length / itemsPerPage)));
	const pagedItems = $derived(
		filteredItems.slice((itemsPage - 1) * itemsPerPage, (itemsPage - 1) * itemsPerPage + itemsPerPage)
	);
	const selected = $derived(items.find((it) => it.code === selectedCode) || null);

	// KPIs
	const kpiCritical = $derived(items.filter((i) => i.status === 'CRITICAL').length);
	const kpiWarning = $derived(items.filter((i) => i.status === 'WARNING').length);
	const kpiRusak = $derived(items.filter((i) => i.status === 'RUSAK').length);
	const kpiTotalCost = $derived(items.reduce((s, i) => s + i.estCost, 0));
	const kpiAvgRul = $derived(
		items.length ? Math.round(items.reduce((s, i) => s + i.rulHours, 0) / items.length) : 0
	);

	// Modal create WO
	let modalOpen = $state(false);
	let modalItem = $state<WoItem | null>(null);
	let modalStart = $state(Date.now());
	let nowTick = $state(Date.now());
	let tickTimer: ReturnType<typeof setInterval> | null = null;
	let woTechnician = $state('');
	let woNotes = $state('');
	let woSaving = $state(false);
	const repairProgress = $derived.by(() => {
		if (!modalItem) return 0;
		const total = modalItem.estCompletionDate.getTime() - modalStart;
		if (total <= 0) return 100;
		return Math.max(0, Math.min(100, ((nowTick - modalStart) / total) * 100));
	});
	const repairCountdown = $derived.by(() => {
		if (!modalItem) return '00:00:00';
		let ms = Math.max(0, modalItem.estCompletionDate.getTime() - nowTick);
		const d = Math.floor(ms / 86_400_000);
		ms -= d * 86_400_000;
		const h = Math.floor(ms / 3_600_000);
		ms -= h * 3_600_000;
		const m = Math.floor(ms / 60_000);
		ms -= m * 60_000;
		const s = Math.floor(ms / 1000);
		const pad = (n: number) => String(n).padStart(2, '0');
		return d > 0 ? `${d}h ${pad(h)}:${pad(m)}:${pad(s)}` : `${pad(h)}:${pad(m)}:${pad(s)}`;
	});

	// Saved WO
	let savedWorkOrders = $state<any[]>([]);
	let woSearch = $state('');
	let woPage = $state(1);
	const woPerPage = 5;
	const filteredSavedWo = $derived.by(() => {
		const q = woSearch.trim().toLowerCase();
		if (!q) return savedWorkOrders;
		return savedWorkOrders.filter((wo: any) =>
			[wo.wo_number, wo.asset_code, wo.equipment_type, wo.component, wo.technician, wo.wo_status, wo.priority, wo.status_unit]
				.filter(Boolean)
				.some((v: string) => String(v).toLowerCase().includes(q))
		);
	});
	const woTotalPages = $derived(Math.max(1, Math.ceil(filteredSavedWo.length / woPerPage)));
	const pagedSavedWo = $derived(
		filteredSavedWo.slice((woPage - 1) * woPerPage, (woPage - 1) * woPerPage + woPerPage)
	);

	// Saved WO detail
	let woDetailOpen = $state(false);
	let woDetail = $state<any>(null);
	let woDetailLoading = $state(false);
	let woMap: any = null;

	let refreshTimer: ReturnType<typeof setInterval> | null = null;
	let ChartLib: any = null;
	const charts: Record<string, any> = {};

	// --- helpers ---
	const statusColor = (s: string) =>
		({ CRITICAL: '#E0413E', WARNING: '#E0A106', RUSAK: '#7A848E', SEHAT: '#1FA971' })[s] ||
		'#7A848E';
	const priorityColor = (p: string) =>
		({ HIGH: '#E0413E', MEDIUM: '#E0A106', LOW: '#3E92CC' })[p] || '#7A848E';
	const woStatusColor = (s: string) =>
		({ OPEN: '#3E92CC', IN_PROGRESS: '#E0A106', COMPLETED: '#1FA971', CANCELLED: '#7A848E' })[s] ||
		'#7A848E';
	const priorityOf = (status: string) =>
		status === 'RUSAK' || status === 'CRITICAL' ? 'HIGH' : status === 'WARNING' ? 'MEDIUM' : 'LOW';
	const hashCode = (s: string) => {
		let h = 0;
		for (let i = 0; i < s.length; i++) h = (h * 31 + s.charCodeAt(i)) >>> 0;
		return h;
	};
	const estCostOf = (code: string, status: string) => {
		const base = status === 'RUSAK' ? 280_000_000 : status === 'CRITICAL' ? 135_000_000 : 48_000_000;
		const factor = 1 + ((hashCode(code) % 40) - 10) / 100;
		return Math.round((base * factor) / 1_000_000) * 1_000_000;
	};
	const lstmComponentsOf = (a: any): { label: string; hours: number }[] => {
		const p = a?.prediction;
		if (!p) return [];
		return [
			{ label: 'Sistem Hidrolik', hours: p.lstm_hydraulic_system },
			{ label: 'Pompa Hidrolik', hours: p.lstm_hydraulic_pump },
			{ label: 'Seal Pompa', hours: p.lstm_pump_seal },
			{ label: 'Sistem Rem', hours: p.lstm_brake_system },
			{ label: 'Brake Caliper', hours: p.lstm_brake_caliper },
			{ label: 'Brake Pad (Rear)', hours: p.lstm_brake_pad },
			{ label: 'Sistem Kemudi', hours: p.lstm_steering_system }
		]
			.filter((c) => typeof c.hours === 'number')
			.sort((x, y) => x.hours - y.hours);
	};

	const fmtRupiah = (n: number) =>
		new Intl.NumberFormat('id-ID', { style: 'currency', currency: 'IDR', maximumFractionDigits: 0 }).format(n);
	const fmtRupiahShort = (n: number) => {
		if (n >= 1_000_000_000) return `Rp ${(n / 1_000_000_000).toFixed(1)} M`;
		if (n >= 1_000_000) return `Rp ${Math.round(n / 1_000_000)} jt`;
		return fmtRupiah(n);
	};
	const fmtHours = (h: number) =>
		h >= 24 ? `${Math.floor(h / 24)} hari ${Math.round(h % 24)} jam` : `${Math.round(h)} jam`;
	const fmtDate = (d: Date) =>
		d.toLocaleString('id-ID', { day: '2-digit', month: 'short', hour: '2-digit', minute: '2-digit' });
	const fmtDateLong = (d: Date | string) =>
		new Date(d).toLocaleString('id-ID', { weekday: 'short', day: '2-digit', month: 'long', hour: '2-digit', minute: '2-digit' });

	function buildItem(u: any, a: any): WoItem {
		const now = Date.now();
		const rul = a?.prediction?.lstm_rul_hours ?? Math.max(2, Math.round((u.health || 50) * 1.5));
		const unc = a?.prediction?.rul_uncertainty ?? Math.round(rul * 0.15);
		const failureMs = now + rul * 3600 * 1000;
		const repairByMs = u.status === 'RUSAK' ? now + 8 * 3600 * 1000 : now + Math.max(8, rul * 0.6) * 3600 * 1000;
		const repairDurationHours = u.status === 'RUSAK' ? 24 : u.status === 'CRITICAL' ? 12 : 6;
		const estCompletionMs = repairByMs + repairDurationHours * 3600 * 1000;
		const comps = lstmComponentsOf(a);
		const componentHealth: { component: string; health: number }[] =
			a?.component_health && a.component_health.length
				? a.component_health
				: comps.slice(0, 6).map((c) => ({ component: c.label, health: Math.max(5, Math.min(100, Math.round(c.hours / 5))) }));
		const shap = [...(a?.shap_contributions || [])]
			.sort((x: any, y: any) => Math.abs(y.value) - Math.abs(x.value))
			.slice(0, 5);
		const twinObj = a?.prediction?.digital_twin;
		const twins = twinObj
			? [
					{ label: 'Brake Twin', hours: twinObj.brake_twin_rul },
					{ label: 'Bearing Twin', hours: twinObj.bearing_twin_rul },
					{ label: 'Hydraulic Twin', hours: twinObj.hydraulic_twin_rul }
				]
			: [];
		return {
			id: u.id,
			code: u.code,
			type: u.jenis_alat_berat_nama || 'Heavy Equipment',
			status: u.status,
			health: u.health ?? 0,
			riskLevel: u.risk_level || a?.risk_level || '-',
			riskScore: Math.round(u.risk_score ?? a?.risk_score ?? 0),
			rulHours: Math.round(rul),
			rulUncertainty: Math.round(unc),
			failureDate: new Date(failureMs),
			repairByDate: new Date(repairByMs),
			repairDurationHours,
			estCompletionDate: new Date(estCompletionMs),
			priority: priorityOf(u.status),
			topComponent: comps[0]?.label || 'Komponen Utama',
			components: componentHealth,
			shap,
			twins,
			estCost: estCostOf(u.code, u.status),
			woId: 'WO-' + String(hashCode(u.code) % 100000).padStart(5, '0')
		};
	}

	async function fetchData() {
		try {
			const res: any = await api.getAnalisaOverview();
			const atRisk = (res.data.units || []).filter((u: any) => ATRISK.includes(u.status));
			const analyses = await Promise.all(
				atRisk.map((u: any) => api.getUnitAnalysis(u.id).then((r: any) => r.data).catch(() => null))
			);
			items = atRisk
				.map((u: any, i: number) => buildItem(u, analyses[i]))
				.sort((a: WoItem, b: WoItem) => a.rulHours - b.rulHours);
			if (items.length) {
				// Preserve the deep-linked (?asset=KODE) selection across refreshes,
				// otherwise keep the current selection, else fall back to the most
				// urgent unit.
				const fromQuery = pageStore.url.searchParams.get('asset');
				const match = fromQuery
					? items.find((it) => it.code.toLowerCase() === fromQuery.toLowerCase())
					: undefined;
				if (!selectedCode || !items.find((it) => it.code === selectedCode)) {
					selectedCode = (match || items[0]).code;
				}
			} else {
				selectedCode = null;
			}
			error = '';
			lastUpdate = new Date().toLocaleTimeString('id-ID');
		} catch (e: any) {
			error = e?.message || 'Gagal memuat data work order.';
		}
	}

	async function fetchWorkOrders() {
		try {
			const res: any = await api.getWorkOrders({ per_page: 100 });
			savedWorkOrders = res?.data?.data || [];
		} catch {
			/* ignore */
		}
	}

	function showToast(ok: boolean, msg: string) {
		woToast = { ok, msg };
		if (woToastTimer) clearTimeout(woToastTimer);
		woToastTimer = setTimeout(() => (woToast = null), 5000);
	}

	function openModal(it: WoItem) {
		modalItem = it;
		modalStart = Date.now();
		nowTick = Date.now();
		woTechnician = '';
		woNotes = '';
		modalOpen = true;
	}
	function closeModal() {
		modalOpen = false;
	}

	async function submitWorkOrder() {
		const it = modalItem;
		if (!it) return;
		woSaving = true;
		try {
			const res: any = await api.createWorkOrder({
				asset_code: it.code,
				equipment_type: it.type,
				status_unit: it.status,
				priority: it.priority,
				component: it.topComponent,
				part_no: 'PRT-' + it.code.replace(/[^A-Za-z0-9]/g, '').toUpperCase().slice(0, 6),
				rul_hours: it.rulHours,
				est_cost: it.estCost,
				scheduled_at: it.repairByDate.toISOString(),
				est_completion_at: it.estCompletionDate.toISOString(),
				technician: woTechnician || undefined,
				notes: woNotes || undefined
			});
			const wo = res?.data;
			showToast(true, `Work Order ${wo?.wo_number || ''} untuk ${it.code} berhasil dibuat.`);
			await fetchWorkOrders();
			closeModal();
		} catch (e: any) {
			showToast(false, e?.message || 'Gagal membuat Work Order.');
		} finally {
			woSaving = false;
		}
	}

	async function updateWoStatus(id: string, wo_status: string) {
		try {
			await api.updateWorkOrder(id, { wo_status });
			await fetchWorkOrders();
			// Menandai COMPLETED mengubah unit menjadi SEHAT → muat ulang daftar
			// unit berisiko & chart agar konsisten tanpa menunggu auto-refresh.
			if (wo_status === 'COMPLETED') {
				await fetchData();
				await tick();
				renderAll();
			}
		} catch (e: any) {
			showToast(false, e?.message || 'Gagal memperbarui status WO.');
		}
	}

	async function renderWoMap() {
		const u = woDetail?.unit;
		if (!u || u.lat == null || u.lng == null) return;
		await tick();
		if (woMap) {
			try {
				woMap.remove();
			} catch {
				/* ignore */
			}
			woMap = null;
		}
		woMap = await createMap(
			'wo-detail-map',
			[
				{
					unit: u.code,
					unit_type: u.jenis_alat_berat_nama || 'Heavy Equipment',
					status: u.status,
					color_hex: statusColor(u.status),
					level: (u.status || '•').charAt(0),
					lat: u.lat,
					lng: u.lng,
					health: u.health
				}
			],
			{ zoom: 14, dark: theme.isDark }
		);
	}

	async function openWoDetail(id: string) {
		woDetailOpen = true;
		woDetailLoading = true;
		woDetail = null;
		if (woMap) {
			try {
				woMap.remove();
			} catch {
				/* ignore */
			}
			woMap = null;
		}
		try {
			const res: any = await api.getWorkOrder(id);
			woDetail = res?.data || null;
		} catch (e: any) {
			showToast(false, e?.message || 'Gagal memuat detail Work Order.');
			woDetailOpen = false;
		} finally {
			woDetailLoading = false;
		}
		await tick();
		renderWoMap();
	}
	function closeWoDetail() {
		woDetailOpen = false;
		if (woMap) {
			try {
				woMap.remove();
			} catch {
				/* ignore */
			}
			woMap = null;
		}
	}

	// --- export ---
	const EXPORT_COLUMNS = [
		{ key: 'wo_number', label: 'WO Number' },
		{ key: 'asset_code', label: 'Unit' },
		{ key: 'equipment_type', label: 'Equipment' },
		{ key: 'status_unit', label: 'Status Unit' },
		{ key: 'priority', label: 'Prioritas' },
		{ key: 'component', label: 'Komponen' },
		{ key: 'part_no', label: 'Part No' },
		{ key: 'rul_hours', label: 'RUL (jam)' },
		{ key: 'est_cost', label: 'Est. Biaya (Rp)' },
		{ key: 'technician', label: 'Teknisi' },
		{ key: 'scheduled_at', label: 'Mulai Perbaikan' },
		{ key: 'est_completion_at', label: 'Est. Selesai' },
		{ key: 'wo_status', label: 'Status WO' },
		{ key: 'notes', label: 'Catatan' },
		{ key: 'created_at', label: 'Dibuat' }
	];
	function cellValue(wo: any, key: string) {
		const v = wo[key];
		if (v == null) return '';
		if (key.endsWith('_at')) return fmtDateLong(v);
		return String(v);
	}
	function downloadBlob(content: string, mime: string, filename: string) {
		const blob = new Blob([content], { type: mime });
		const url = URL.createObjectURL(blob);
		const a = document.createElement('a');
		a.href = url;
		a.download = filename;
		document.body.appendChild(a);
		a.click();
		document.body.removeChild(a);
		URL.revokeObjectURL(url);
	}
	function exportCsv() {
		const rows = filteredSavedWo;
		const esc = (s: string) => `"${String(s).replace(/"/g, '""')}"`;
		const header = EXPORT_COLUMNS.map((c) => esc(c.label)).join(',');
		const body = rows.map((wo: any) => EXPORT_COLUMNS.map((c) => esc(cellValue(wo, c.key))).join(',')).join('\n');
		const stamp = new Date().toISOString().slice(0, 10);
		downloadBlob('\uFEFF' + header + '\n' + body, 'text/csv;charset=utf-8;', `work-orders-${stamp}.csv`);
	}
	function exportExcel() {
		const rows = filteredSavedWo;
		const esc = (s: string) => String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
		const head = '<tr>' + EXPORT_COLUMNS.map((c) => `<th style="background:#1d242e;color:#fff;padding:6px;border:1px solid #ccc">${esc(c.label)}</th>`).join('') + '</tr>';
		const body = rows.map((wo: any) => '<tr>' + EXPORT_COLUMNS.map((c) => `<td style="padding:6px;border:1px solid #ccc">${esc(cellValue(wo, c.key))}</td>`).join('') + '</tr>').join('');
		const html = `<html xmlns:o="urn:schemas-microsoft-com:office:office" xmlns:x="urn:schemas-microsoft-com:office:excel" xmlns="http://www.w3.org/TR/REC-html40"><head><meta charset="UTF-8"></head><body><table>${head}${body}</table></body></html>`;
		const stamp = new Date().toISOString().slice(0, 10);
		downloadBlob(html, 'application/vnd.ms-excel', `work-orders-${stamp}.xls`);
	}

	// --- charts ---
	function css(v: string) {
		if (typeof window === 'undefined') return '';
		return getComputedStyle(document.documentElement).getPropertyValue(v).trim();
	}
	function chartTheme() {
		return {
			tick: css('--text-muted') || '#5d6b7a',
			grid: css('--border') || '#d7dde4',
			axis: css('--border-strong') || '#c2cad3',
			text: css('--text') || '#1b2128'
		};
	}
	function upsertChart(key: string, canvasId: string, config: any) {
		const el = document.getElementById(canvasId) as HTMLCanvasElement | null;
		if (!el || !ChartLib) return;
		if (charts[key]) {
			charts[key].data = config.data;
			if (config.options) charts[key].options = config.options;
			charts[key].update('none');
		} else {
			charts[key] = new ChartLib(el, config);
		}
	}
	const arcValueLabels = {
		id: 'arcValueLabels',
		afterDatasetsDraw(chart: any) {
			const { ctx } = chart;
			const meta = chart.getDatasetMeta(0);
			const ds = chart.data.datasets[0]?.data || [];
			meta.data.forEach((arc: any, i: number) => {
				const val = ds[i];
				if (!val) return;
				const pos = arc.tooltipPosition();
				ctx.save();
				ctx.fillStyle = '#ffffff';
				ctx.font = 'bold 14px Inter, sans-serif';
				ctx.textAlign = 'center';
				ctx.textBaseline = 'middle';
				ctx.shadowColor = 'rgba(0,0,0,0.35)';
				ctx.shadowBlur = 3;
				ctx.fillText(String(val), pos.x, pos.y);
				ctx.restore();
			});
		}
	};

	function renderFleetCharts() {
		const t = chartTheme();
		const list = items;
		upsertChart('woStatus', 'woStatus', {
			type: 'doughnut',
			data: {
				labels: ['Critical', 'Warning', 'Rusak'],
				datasets: [{ data: [kpiCritical, kpiWarning, kpiRusak], backgroundColor: ['#E0413E', '#E0A106', '#7A848E'], borderWidth: 0 }]
			},
			plugins: [arcValueLabels],
			options: { responsive: true, maintainAspectRatio: false, cutout: '62%', plugins: { legend: { position: 'bottom', labels: { color: t.text, font: { size: 11 } } } } }
		});

		const prio = ['HIGH', 'MEDIUM', 'LOW'].map((p) => list.filter((i) => i.priority === p).length);
		upsertChart('woPriority', 'woPriority', {
			type: 'doughnut',
			data: { labels: ['High', 'Medium', 'Low'], datasets: [{ data: prio, backgroundColor: ['#E0413E', '#E0A106', '#3E92CC'], borderWidth: 0 }] },
			plugins: [arcValueLabels],
			options: { responsive: true, maintainAspectRatio: false, cutout: '62%', plugins: { legend: { position: 'bottom', labels: { color: t.text, font: { size: 11 } } } } }
		});

		const byRul = [...list].sort((a, b) => a.rulHours - b.rulHours).slice(0, 12);
		upsertChart('woRul', 'woRul', {
			type: 'bar',
			data: { labels: byRul.map((i) => i.code), datasets: [{ label: 'RUL (jam)', data: byRul.map((i) => i.rulHours), backgroundColor: byRul.map((i) => statusColor(i.status)), borderRadius: 5 }] },
			options: {
				indexAxis: 'y',
				responsive: true,
				maintainAspectRatio: false,
				plugins: { legend: { display: false }, tooltip: { callbacks: { label: (c: any) => `${c.raw} jam tersisa` } } },
				scales: { x: { beginAtZero: true, ticks: { color: t.tick, font: { family: 'JetBrains Mono', size: 9 } }, grid: { color: t.grid } }, y: { ticks: { color: t.text, font: { weight: 'bold', size: 10 } }, grid: { display: false } } }
			}
		});

		const byCost = [...list].sort((a, b) => b.estCost - a.estCost).slice(0, 12);
		upsertChart('woCost', 'woCost', {
			type: 'bar',
			data: { labels: byCost.map((i) => i.code), datasets: [{ label: 'Estimasi Biaya (juta Rp)', data: byCost.map((i) => Math.round(i.estCost / 1_000_000)), backgroundColor: '#3E92CC', borderRadius: 5 }] },
			options: {
				responsive: true,
				maintainAspectRatio: false,
				plugins: { legend: { display: false }, tooltip: { callbacks: { label: (c: any) => `Rp ${c.raw} juta` } } },
				scales: { x: { ticks: { color: t.text, font: { family: 'JetBrains Mono', size: 9 } }, grid: { display: false } }, y: { beginAtZero: true, ticks: { color: t.tick, font: { size: 9 } }, grid: { color: t.grid } } }
			}
		});

		const days = 14;
		const now = Date.now();
		const labels: string[] = [];
		const cumulative: number[] = [];
		for (let d = 1; d <= days; d++) {
			const until = now + d * 24 * 3600 * 1000;
			labels.push(`H+${d}`);
			cumulative.push(list.filter((i) => i.failureDate.getTime() <= until).length);
		}
		upsertChart('woTimeline', 'woTimeline', {
			type: 'line',
			data: { labels, datasets: [{ label: 'Akumulasi unit jatuh tempo perbaikan', data: cumulative, borderColor: '#E0413E', backgroundColor: 'rgba(224,65,62,0.12)', fill: true, tension: 0.35, pointRadius: 3, pointBackgroundColor: '#E0413E' }] },
			options: {
				responsive: true,
				maintainAspectRatio: false,
				plugins: { legend: { labels: { color: t.text, font: { size: 11 } } } },
				scales: { x: { ticks: { color: t.tick, font: { family: 'JetBrains Mono', size: 9 } }, grid: { color: t.grid } }, y: { beginAtZero: true, ticks: { color: t.tick, stepSize: 1 }, grid: { color: t.grid } } }
			}
		});
	}

	function renderDetailCharts() {
		const t = chartTheme();
		const s = selected;
		if (!s) return;
		upsertChart('woRadar', 'woRadar', {
			type: 'radar',
			data: { labels: s.components.map((c) => c.component), datasets: [{ label: `Health ${s.code}`, data: s.components.map((c) => c.health), backgroundColor: 'rgba(62,146,204,0.18)', borderColor: '#3E92CC', pointBackgroundColor: '#3E92CC' }] },
			options: {
				responsive: true,
				maintainAspectRatio: false,
				plugins: { legend: { display: false } },
				scales: { r: { suggestedMin: 0, suggestedMax: 100, angleLines: { color: t.grid }, grid: { color: t.grid }, pointLabels: { color: t.text, font: { size: 10 } }, ticks: { display: false } } }
			}
		});
		upsertChart('woShap', 'woShap', {
			type: 'bar',
			data: { labels: s.shap.map((x) => x.feature), datasets: [{ label: 'Kontribusi SHAP (%)', data: s.shap.map((x) => Math.round(x.value)), backgroundColor: s.shap.map((x) => (x.value >= 0 ? '#E0413E' : '#1FA971')), borderRadius: 5 }] },
			options: {
				indexAxis: 'y',
				responsive: true,
				maintainAspectRatio: false,
				plugins: { legend: { display: false } },
				scales: { x: { ticks: { color: t.tick, font: { size: 9 } }, grid: { color: t.grid } }, y: { ticks: { color: t.text, font: { size: 10 } }, grid: { display: false } } }
			}
		});
	}

	function renderAll() {
		renderFleetCharts();
		renderDetailCharts();
	}

	async function refreshAll() {
		await fetchData();
		await tick();
		renderAll();
	}

	async function selectUnit(code: string) {
		selectedCode = code;
		await tick();
		renderDetailCharts();
	}

	onMount(async () => {
		const mod = await import('chart.js/auto');
		ChartLib = mod.default;
		await fetchData();
		isLoading = false;
		await tick();
		renderAll();
		await fetchWorkOrders();

		// Deep-link ?asset=KODE (from Telegram) → open the create-WO modal.
		const assetQuery = pageStore.url.searchParams.get('asset');
		if (assetQuery) {
			const target = items.find((it) => it.code.toLowerCase() === assetQuery.toLowerCase());
			if (target) {
				selectedCode = target.code;
				await tick();
				renderDetailCharts();
				openModal(target);
			} else {
				showToast(
					false,
					`Unit ${assetQuery} tidak berstatus berisiko (CRITICAL/WARNING/RUSAK), jadi Work Order tidak dapat dibuat.`
				);
			}
		}

		refreshTimer = setInterval(() => {
			if (autoRefresh) refreshAll();
		}, 15000);
		tickTimer = setInterval(() => (nowTick = Date.now()), 1000);
	});

	onDestroy(() => {
		if (refreshTimer) clearInterval(refreshTimer);
		if (tickTimer) clearInterval(tickTimer);
		if (woToastTimer) clearTimeout(woToastTimer);
		if (woMap) {
			try {
				woMap.remove();
			} catch {
				/* ignore */
			}
		}
		Object.values(charts).forEach((c) => c?.destroy());
	});

	// Tutup dialog teratas dengan tombol Escape.
	function onKeydown(e: KeyboardEvent) {
		if (e.key !== 'Escape') return;
		if (modalOpen) closeModal();
		else if (woDetailOpen) closeWoDetail();
	}

	$effect(() => {
		const dark = theme.isDark;
		tick().then(() => {
			if (ChartLib) renderAll();
			document
				.querySelectorAll('#wo-detail-map')
				.forEach((el) => el.classList.toggle('map-dark', dark));
		});
	});

	// Clamp pagination when filters shrink the list.
	$effect(() => {
		if (itemsPage > itemsTotalPages) itemsPage = itemsTotalPages;
	});
	$effect(() => {
		if (woPage > woTotalPages) woPage = woTotalPages;
	});
</script>

<svelte:head><title>Work Order — Pratyaksa</title></svelte:head>
<svelte:window onkeydown={onKeydown} />

<header class="flex justify-between items-start mb-8 flex-wrap gap-4">
	<div>
		<h1 class="font-display text-4xl md:text-5xl font-bold uppercase tracking-wide leading-none">Work Order</h1>
		<p class="mt-2 text-[color:var(--text-muted)]">Estimasi perbaikan unit CRITICAL, WARNING &amp; RUSAK — dipicu dari alert Telegram.</p>
	</div>
	<div class="flex items-center gap-3">
		<div class="panel-flat px-3 py-2 text-[10px] font-mono text-[color:var(--text-muted)]">Update<br /><span class="font-semibold text-[color:var(--text)]">{lastUpdate || '—'}</span></div>
	</div>
</header>

{#if error}<div class="mb-6 px-4 py-3 rounded-xl bg-critical/10 border border-critical/40 text-critical font-semibold">⚠️ {error}</div>{/if}
{#if woToast}
	<div class="mb-4 px-4 py-2.5 rounded-xl text-sm font-semibold {woToast.ok ? 'bg-healthy/10 border border-healthy/40 text-healthy' : 'bg-critical/10 border border-critical/40 text-critical'}">{woToast.msg}</div>
{/if}

{#if isLoading}
	<div class="flex items-center justify-center h-96 font-semibold text-[color:var(--text-faint)] uppercase tracking-widest">Memuat work order…</div>
{:else}
	<!-- KPI -->
	<div class="grid grid-cols-2 lg:grid-cols-5 gap-4 mb-7">
		<div class="panel-flat p-5"><p class="text-[10px] font-semibold uppercase tracking-wider text-[color:var(--text-muted)] mb-1">Critical</p><p class="font-display text-4xl font-bold text-critical">{kpiCritical}</p></div>
		<div class="panel-flat p-5"><p class="text-[10px] font-semibold uppercase tracking-wider text-[color:var(--text-muted)] mb-1">Warning</p><p class="font-display text-4xl font-bold text-warning">{kpiWarning}</p></div>
		<div class="panel-flat p-5"><p class="text-[10px] font-semibold uppercase tracking-wider text-[color:var(--text-muted)] mb-1">Rusak</p><p class="font-display text-4xl font-bold text-rusak">{kpiRusak}</p></div>
		<div class="panel-flat p-5"><p class="text-[10px] font-semibold uppercase tracking-wider text-[color:var(--text-muted)] mb-1">Rata-rata RUL</p><p class="font-display text-4xl font-bold text-steel">{kpiAvgRul}<span class="text-base font-semibold"> jam</span></p></div>
		<div class="panel-flat p-5"><p class="text-[10px] font-semibold uppercase tracking-wider text-[color:var(--text-muted)] mb-1">Est. Biaya Total</p><p class="font-display text-3xl font-bold text-amber">{fmtRupiahShort(kpiTotalCost)}</p></div>
	</div>

	{#if !items.length}
		<div class="panel-flat p-10 text-center text-[color:var(--text-muted)]">🎉 Tidak ada unit berstatus CRITICAL / WARNING / RUSAK saat ini. Semua armada dalam kondisi sehat.</div>
	{:else}
		<!-- Grid Chart Fleet -->
		<div class="grid grid-cols-1 lg:grid-cols-3 gap-5 mb-6">
			<div class="panel-flat p-5"><h3 class="font-display text-lg font-bold uppercase tracking-wide mb-3">Distribusi Status</h3><div style="height:224px;"><canvas id="woStatus"></canvas></div></div>
			<div class="panel-flat p-5"><h3 class="font-display text-lg font-bold uppercase tracking-wide mb-3">Distribusi Prioritas</h3><div style="height:224px;"><canvas id="woPriority"></canvas></div></div>
			<div class="panel-flat p-5"><h3 class="font-display text-lg font-bold uppercase tracking-wide mb-3">RUL per Unit (jam)</h3><div style="height:224px;"><canvas id="woRul"></canvas></div></div>
		</div>

		<div class="grid grid-cols-1 lg:grid-cols-2 gap-5 mb-6">
			<div class="panel-flat p-5"><h3 class="font-display text-lg font-bold uppercase tracking-wide mb-3">Estimasi Biaya per Unit</h3><div style="height:256px;"><canvas id="woCost"></canvas></div></div>
			<div class="panel-flat p-5"><h3 class="font-display text-lg font-bold uppercase tracking-wide mb-3">Proyeksi Jatuh Tempo Perbaikan (14 hari)</h3><div style="height:256px;"><canvas id="woTimeline"></canvas></div></div>
		</div>

		<!-- Tabel Work Order -->
		<div class="panel-flat p-5 mb-6">
			<div class="flex items-center justify-between mb-4 flex-wrap gap-3">
				<h3 class="font-display text-xl font-bold uppercase tracking-wide">Daftar Work Order</h3>
				<div class="flex gap-1.5">
					{#each ['ALL', 'CRITICAL', 'WARNING', 'RUSAK'] as f (f)}
						<button class="btn !py-1.5 !px-3 text-[11px] {statusFilter === f ? 'bg-amber text-graphite-900 border-amber' : 'btn-ghost'}" onclick={() => { statusFilter = f as any; itemsPage = 1; }}>{f === 'ALL' ? 'Semua' : f}</button>
					{/each}
				</div>
			</div>
			<div class="overflow-x-auto">
				<table class="w-full text-sm" style="min-width:720px;">
					<thead>
						<tr class="text-left text-[10px] uppercase tracking-wider text-[color:var(--text-muted)] border-b border-[color:var(--border)]">
							<th class="py-2.5 pr-3">WO ID</th><th class="py-2.5 pr-3">Unit</th><th class="py-2.5 pr-3">Status</th><th class="py-2.5 pr-3">Prioritas</th><th class="py-2.5 pr-3">RUL</th><th class="py-2.5 pr-3">Komponen Kritis</th><th class="py-2.5 pr-3">Perbaikan Sebelum</th><th class="py-2.5 pr-3">Est. Biaya</th><th class="py-2.5"></th>
						</tr>
					</thead>
					<tbody>
						{#each pagedItems as it (it.id)}
							<tr
								class="border-b border-[color:var(--border)] cursor-pointer hover:bg-[color:var(--surface-2)] transition-colors {selectedCode === it.code ? 'bg-[color:var(--surface-2)]' : ''}"
								onclick={() => selectUnit(it.code)}
							>
								<td class="py-2.5 pr-3 font-mono text-[11px]">{it.woId}</td>
								<td class="py-2.5 pr-3 font-semibold">{it.code}<span class="block text-[10px] text-[color:var(--text-muted)] font-normal">{it.type}</span></td>
								<td class="py-2.5 pr-3"><span class="px-2 py-0.5 rounded-full text-[10px] font-bold text-white" style="background:{statusColor(it.status)}">{it.status}</span></td>
								<td class="py-2.5 pr-3"><span class="px-2 py-0.5 rounded-full text-[10px] font-bold text-white" style="background:{priorityColor(it.priority)}">{it.priority}</span></td>
								<td class="py-2.5 pr-3 font-mono">{fmtHours(it.rulHours)}</td>
								<td class="py-2.5 pr-3">{it.topComponent}</td>
								<td class="py-2.5 pr-3 font-mono text-[11px]">{fmtDate(it.repairByDate)}</td>
								<td class="py-2.5 pr-3 font-semibold text-amber">{fmtRupiahShort(it.estCost)}</td>
								<td class="py-2.5 text-right"><button class="btn btn-ghost !py-1.5 !px-3 text-[11px] text-steel" onclick={(e) => { e.stopPropagation(); openModal(it); }}>Detail</button></td>
							</tr>
						{/each}
						{#if !filteredItems.length}
							<tr><td colspan="9" class="py-6 text-center text-[color:var(--text-muted)]">Tidak ada unit berisiko untuk filter ini.</td></tr>
						{/if}
					</tbody>
				</table>
			</div>
			{#if itemsTotalPages > 1}
				<div class="flex items-center justify-between mt-4">
					<p class="text-xs text-[color:var(--text-muted)]">Menampilkan {pagedItems.length} dari {filteredItems.length} unit</p>
					<div class="flex items-center gap-1.5">
						<button class="btn btn-ghost !py-1.5 !px-3 text-[11px] disabled:opacity-40" disabled={itemsPage === 1} onclick={() => (itemsPage = Math.max(1, itemsPage - 1))}>‹ Prev</button>
						<span class="text-xs font-mono px-2">{itemsPage} / {itemsTotalPages}</span>
						<button class="btn btn-ghost !py-1.5 !px-3 text-[11px] disabled:opacity-40" disabled={itemsPage === itemsTotalPages} onclick={() => (itemsPage = Math.min(itemsTotalPages, itemsPage + 1))}>Next ›</button>
					</div>
				</div>
			{/if}
		</div>

		<!-- Detail Unit Terpilih -->
		{#if selected}
			<div class="panel-raised p-6 mb-4">
				<div class="flex items-start justify-between flex-wrap gap-4 mb-5">
					<div>
						<p class="text-[10px] font-semibold uppercase tracking-wider text-[color:var(--text-muted)]">{selected.woId} · Detail Work Order</p>
						<h2 class="font-display text-3xl font-bold tracking-wide">{selected.code}</h2>
						<p class="text-[color:var(--text-muted)] text-sm">{selected.type}</p>
					</div>
					<div class="flex items-center gap-2">
						<span class="px-3 py-1 rounded-full text-xs font-bold text-white" style="background:{statusColor(selected.status)}">{selected.status}</span>
						<span class="px-3 py-1 rounded-full text-xs font-bold text-white" style="background:{priorityColor(selected.priority)}">PRIORITAS {selected.priority}</span>
					</div>
				</div>

				<div class="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
					<div class="panel-flat p-4"><p class="text-[10px] font-semibold uppercase tracking-wider text-[color:var(--text-muted)] mb-1">Sisa Umur (RUL)</p><p class="font-display text-2xl font-bold text-critical">{fmtHours(selected.rulHours)}</p><p class="text-[10px] text-[color:var(--text-muted)]">± {selected.rulUncertainty} jam</p></div>
					<div class="panel-flat p-4"><p class="text-[10px] font-semibold uppercase tracking-wider text-[color:var(--text-muted)] mb-1">Estimasi Breakdown</p><p class="font-display text-xl font-bold">{fmtDate(selected.failureDate)}</p></div>
					<div class="panel-flat p-4"><p class="text-[10px] font-semibold uppercase tracking-wider text-[color:var(--text-muted)] mb-1">Perbaikan Sebelum</p><p class="font-display text-xl font-bold text-warning">{fmtDate(selected.repairByDate)}</p></div>
					<div class="panel-flat p-4"><p class="text-[10px] font-semibold uppercase tracking-wider text-[color:var(--text-muted)] mb-1">Estimasi Biaya</p><p class="font-display text-2xl font-bold text-amber">{fmtRupiahShort(selected.estCost)}</p></div>
				</div>

				<div class="grid grid-cols-1 lg:grid-cols-2 gap-5 mb-6">
					<div class="panel-flat p-5"><h3 class="font-display text-lg font-bold uppercase tracking-wide mb-3">Kesehatan Komponen</h3><div style="height:256px;"><canvas id="woRadar"></canvas></div></div>
					<div class="panel-flat p-5"><h3 class="font-display text-lg font-bold uppercase tracking-wide mb-3">Kontributor Risiko (SHAP)</h3><div style="height:256px;"><canvas id="woShap"></canvas></div></div>
				</div>

				{#if selected.twins.length}
					<div class="grid grid-cols-1 md:grid-cols-3 gap-4">
						{#each selected.twins as tw (tw.label)}
							<div class="panel-flat p-4 text-center"><p class="text-[10px] font-semibold uppercase tracking-wider text-[color:var(--text-muted)] mb-1">{tw.label}</p><p class="font-display text-2xl font-bold text-steel">{fmtHours(tw.hours)}</p></div>
						{/each}
					</div>
				{/if}
			</div>
		{/if}

		<!-- Work Order Tersimpan -->
		{#if savedWorkOrders.length}
			<div class="panel-flat p-5 mb-6">
				<div class="flex items-center justify-between mb-4 flex-wrap gap-3">
					<h3 class="font-display text-xl font-bold uppercase tracking-wide">Work Order Tersimpan</h3>
					<div class="flex items-center gap-2 flex-wrap">
						<div class="relative">
							<svg class="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-[color:var(--text-faint)]" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2"><circle cx="11" cy="11" r="8" /><path d="m21 21-4.3-4.3" /></svg>
							<input bind:value={woSearch} oninput={() => (woPage = 1)} type="text" placeholder="Cari WO / unit / komponen…" class="pl-9 pr-3 py-2 rounded-xl bg-[color:var(--surface-2)] border border-[color:var(--border)] text-sm focus:outline-none focus:border-amber" style="width:15rem;" />
						</div>
						<button class="btn btn-ghost !py-2 !px-3 text-[11px] font-semibold" onclick={exportCsv}>
							<svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" /><polyline points="7 10 12 15 17 10" /><line x1="12" y1="15" x2="12" y2="3" /></svg>
							CSV
						</button>
						<button class="btn btn-ghost !py-2 !px-3 text-[11px] font-semibold text-healthy" onclick={exportExcel}>
							<svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" /><polyline points="7 10 12 15 17 10" /><line x1="12" y1="15" x2="12" y2="3" /></svg>
							Excel
						</button>
					</div>
				</div>
				<div class="overflow-x-auto">
					<table class="w-full text-sm" style="min-width:760px;">
						<thead>
							<tr class="text-left text-[10px] uppercase tracking-wider text-[color:var(--text-muted)] border-b border-[color:var(--border)]">
								<th class="py-2.5 pr-3">WO Number</th><th class="py-2.5 pr-3">Unit</th><th class="py-2.5 pr-3">Komponen</th><th class="py-2.5 pr-3">Prioritas</th><th class="py-2.5 pr-3">Teknisi</th><th class="py-2.5 pr-3">Est. Selesai</th><th class="py-2.5 pr-3">Status</th><th class="py-2.5"></th>
							</tr>
						</thead>
						<tbody>
							{#each pagedSavedWo as wo (wo.id)}
								<tr class="border-b border-[color:var(--border)] hover:bg-[color:var(--surface-2)] transition-colors">
									<td class="py-2.5 pr-3 font-mono text-[11px]">{wo.wo_number}</td>
									<td class="py-2.5 pr-3 font-semibold">{wo.asset_code}</td>
									<td class="py-2.5 pr-3">{wo.component}</td>
									<td class="py-2.5 pr-3"><span class="px-2 py-0.5 rounded-full text-[10px] font-bold text-white" style="background:{priorityColor(wo.priority)}">{wo.priority}</span></td>
									<td class="py-2.5 pr-3">{wo.technician || '—'}</td>
									<td class="py-2.5 pr-3 font-mono text-[11px]">{wo.est_completion_at ? fmtDateLong(wo.est_completion_at) : '—'}</td>
									<td class="py-2.5 pr-3"><span class="px-2 py-0.5 rounded-full text-[10px] font-bold text-white" style="background:{woStatusColor(wo.wo_status)}">{wo.wo_status}</span></td>
									<td class="py-2.5 text-right whitespace-nowrap">
										<button class="btn btn-ghost !py-1 !px-2 text-[10px] text-steel" onclick={() => openWoDetail(wo.id)}>Detail</button>
										{#if wo.wo_status === 'OPEN'}<button class="btn btn-ghost !py-1 !px-2 text-[10px] text-warning" onclick={() => updateWoStatus(wo.id, 'IN_PROGRESS')}>Mulai</button>{/if}
										{#if wo.wo_status === 'IN_PROGRESS'}<button class="btn btn-ghost !py-1 !px-2 text-[10px] text-healthy" onclick={() => updateWoStatus(wo.id, 'COMPLETED')}>Selesai</button>{/if}
									</td>
								</tr>
							{/each}
							{#if !filteredSavedWo.length}
								<tr><td colspan="8" class="py-6 text-center text-[color:var(--text-muted)]">Tidak ada WO yang cocok dengan pencarian.</td></tr>
							{/if}
						</tbody>
					</table>
				</div>
				{#if woTotalPages > 1}
					<div class="flex items-center justify-between mt-4">
						<p class="text-xs text-[color:var(--text-muted)]">Menampilkan {pagedSavedWo.length} dari {filteredSavedWo.length} WO</p>
						<div class="flex items-center gap-1.5">
							<button class="btn btn-ghost !py-1.5 !px-3 text-[11px] disabled:opacity-40" disabled={woPage === 1} onclick={() => (woPage = Math.max(1, woPage - 1))}>‹ Prev</button>
							<span class="text-xs font-mono px-2">{woPage} / {woTotalPages}</span>
							<button class="btn btn-ghost !py-1.5 !px-3 text-[11px] disabled:opacity-40" disabled={woPage === woTotalPages} onclick={() => (woPage = Math.min(woTotalPages, woPage + 1))}>Next ›</button>
						</div>
					</div>
				{/if}
			</div>
		{/if}
	{/if}
{/if}

<!-- ===== MODAL DETAIL WORK ORDER (create) ===== -->
{#if modalOpen && modalItem}
	<div class="fixed inset-0 z-[100] flex items-center justify-center p-4" style="background:rgba(12,16,20,0.6);backdrop-filter:blur(3px);" role="presentation">
		<div class="modal-card w-full flex flex-col max-h-[90vh] anim-pop" style="max-width:56rem;">
			<div class="flex items-start justify-between gap-4 p-6 border-b border-[color:var(--border)]">
				<div>
					<p class="text-[10px] font-semibold uppercase tracking-wider text-[color:var(--text-muted)]">{modalItem.woId} · Detail Lengkap</p>
					<h2 class="font-display text-3xl font-bold tracking-wide">{modalItem.code}</h2>
					<p class="text-[color:var(--text-muted)] text-sm">{modalItem.type}</p>
				</div>
				<div class="flex items-center gap-2">
					<span class="px-3 py-1 rounded-full text-xs font-bold text-white" style="background:{statusColor(modalItem.status)}">{modalItem.status}</span>
					<span class="px-3 py-1 rounded-full text-xs font-bold text-white" style="background:{priorityColor(modalItem.priority)}">{modalItem.priority}</span>
					<button class="btn btn-ghost !p-2 ml-1" aria-label="Tutup" onclick={closeModal}>
						<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2.5"><path d="M6 18L18 6M6 6l12 12" /></svg>
					</button>
				</div>
			</div>

			<div class="p-6 overflow-y-auto" style="max-height:calc(90vh - 110px);">
				<!-- Progress ring -->
				<div class="panel-flat p-6 mb-6">
					<div class="flex flex-col md:flex-row items-center gap-6">
						<div class="wo-ring shrink-0" style="--p:{repairProgress}">
							<div class="wo-ring-inner">
								<span class="font-display text-2xl font-bold text-amber" style="font-variant-numeric:tabular-nums;">{repairCountdown}</span>
								<span class="text-[9px] uppercase tracking-wider text-[color:var(--text-muted)]">menuju selesai</span>
							</div>
						</div>
						<div class="flex-1 w-full">
							<p class="text-[10px] font-semibold uppercase tracking-wider text-[color:var(--text-muted)] mb-1">Estimasi Perbaikan Selesai</p>
							<p class="font-display text-2xl font-bold mb-1">{fmtDateLong(modalItem.estCompletionDate)}</p>
							<p class="text-sm text-[color:var(--text-muted)] mb-3">
								Mulai perbaikan: <span class="font-semibold text-[color:var(--text)]">{fmtDateLong(modalItem.repairByDate)}</span> ·
								Durasi estimasi: <span class="font-semibold text-[color:var(--text)]">{modalItem.repairDurationHours} jam</span>
							</p>
							<div class="wo-bar"><div class="wo-bar-fill" style="width:{repairProgress}%"></div></div>
							<div class="flex justify-between text-[10px] text-[color:var(--text-muted)] mt-1 font-mono">
								<span>{Math.round(repairProgress)}% berjalan</span>
								<span>selesai {Math.round(100 - repairProgress)}% lagi</span>
							</div>
						</div>
					</div>
				</div>

				<!-- Ringkasan angka -->
				<div class="grid grid-cols-2 md:grid-cols-4 gap-3 mb-6">
					<div class="panel-flat p-4"><p class="text-[10px] uppercase tracking-wider text-[color:var(--text-muted)] mb-1">Sisa Umur (RUL)</p><p class="font-display text-xl font-bold text-critical">{fmtHours(modalItem.rulHours)}</p><p class="text-[10px] text-[color:var(--text-muted)]">± {modalItem.rulUncertainty} jam</p></div>
					<div class="panel-flat p-4"><p class="text-[10px] uppercase tracking-wider text-[color:var(--text-muted)] mb-1">Risk Score</p><p class="font-display text-xl font-bold text-warning">{modalItem.riskScore}</p><p class="text-[10px] text-[color:var(--text-muted)]">{modalItem.riskLevel}</p></div>
					<div class="panel-flat p-4"><p class="text-[10px] uppercase tracking-wider text-[color:var(--text-muted)] mb-1">Estimasi Breakdown</p><p class="font-display text-base font-bold">{fmtDate(modalItem.failureDate)}</p></div>
					<div class="panel-flat p-4"><p class="text-[10px] uppercase tracking-wider text-[color:var(--text-muted)] mb-1">Estimasi Biaya</p><p class="font-display text-xl font-bold text-amber">{fmtRupiahShort(modalItem.estCost)}</p></div>
				</div>

				<div class="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-6">
					<div>
						<h3 class="font-display text-lg font-bold uppercase tracking-wide mb-3">Kesehatan Komponen</h3>
						<div class="space-y-2.5">
							{#each modalItem.components as c (c.component)}
								<div>
									<div class="flex justify-between text-xs mb-1"><span class="font-semibold">{c.component}</span><span class="font-mono" style="color:{c.health < 40 ? '#E0413E' : c.health < 70 ? '#E0A106' : '#1FA971'}">{Math.round(c.health)}%</span></div>
									<div class="wo-bar" style="height:8px;"><div class="wo-bar-fill" style="width:{c.health}%;background:{c.health < 40 ? '#E0413E' : c.health < 70 ? '#E0A106' : '#1FA971'}"></div></div>
								</div>
							{/each}
						</div>
					</div>
					<div>
						<h3 class="font-display text-lg font-bold uppercase tracking-wide mb-3">Kontributor Risiko (SHAP)</h3>
						<div class="space-y-2.5">
							{#each modalItem.shap as sh (sh.feature)}
								<div>
									<div class="flex justify-between text-xs mb-1"><span class="font-semibold">{sh.feature}</span><span class="font-mono" style="color:{sh.value >= 0 ? '#E0413E' : '#1FA971'}">{sh.value >= 0 ? '+' : ''}{Math.round(sh.value)}%</span></div>
									<div class="wo-bar" style="height:8px;"><div class="wo-bar-fill" style="width:{Math.min(100, Math.abs(sh.value))}%;background:{sh.value >= 0 ? '#E0413E' : '#1FA971'}"></div></div>
								</div>
							{/each}
							{#if !modalItem.shap.length}<p class="text-sm text-[color:var(--text-muted)]">Data SHAP tidak tersedia.</p>{/if}
						</div>
					</div>
				</div>

				{#if modalItem.twins.length}
					<div class="grid grid-cols-3 gap-3 mb-6">
						{#each modalItem.twins as tw (tw.label)}
							<div class="panel-flat p-3 text-center"><p class="text-[10px] uppercase tracking-wider text-[color:var(--text-muted)] mb-1">{tw.label}</p><p class="font-display text-lg font-bold text-steel">{fmtHours(tw.hours)}</p></div>
						{/each}
					</div>
				{/if}

				<div class="panel-flat p-5">
					<h3 class="font-display text-lg font-bold uppercase tracking-wide mb-4">Buat Work Order</h3>
					<div class="grid grid-cols-1 md:grid-cols-2 gap-4 mb-4">
						<div>
							<label for="wo-tech" class="block text-[10px] font-semibold uppercase tracking-wider text-[color:var(--text-muted)] mb-1.5">Teknisi</label>
							<input id="wo-tech" bind:value={woTechnician} type="text" placeholder="Nama mekanik / tim" class="w-full px-3 py-2.5 rounded-xl bg-[color:var(--surface-2)] border border-[color:var(--border)] text-sm focus:outline-none focus:border-amber" />
						</div>
						<div>
							<label for="wo-comp" class="block text-[10px] font-semibold uppercase tracking-wider text-[color:var(--text-muted)] mb-1.5">Komponen Target</label>
							<input id="wo-comp" value={modalItem.topComponent} readonly class="w-full px-3 py-2.5 rounded-xl bg-[color:var(--surface-2)] border border-[color:var(--border)] text-sm opacity-70" />
						</div>
					</div>
					<div class="mb-4">
						<label for="wo-notes" class="block text-[10px] font-semibold uppercase tracking-wider text-[color:var(--text-muted)] mb-1.5">Catatan</label>
						<textarea id="wo-notes" bind:value={woNotes} rows="2" placeholder="Instruksi tambahan untuk teknisi…" class="w-full px-3 py-2.5 rounded-xl bg-[color:var(--surface-2)] border border-[color:var(--border)] text-sm focus:outline-none focus:border-amber"></textarea>
					</div>
					<div class="flex justify-end gap-2">
						<button class="btn btn-ghost !py-2.5 text-sm" onclick={closeModal}>Batal</button>
						<button class="btn !py-2.5 text-sm bg-amber text-graphite-900 border-amber font-bold disabled:opacity-60" disabled={woSaving} onclick={submitWorkOrder}>{woSaving ? 'Menyimpan…' : 'Simpan Work Order'}</button>
					</div>
				</div>
			</div>
		</div>
	</div>
{/if}

<!-- ===== MODAL DETAIL WORK ORDER TERSIMPAN ===== -->
{#if woDetailOpen}
	<div class="fixed inset-0 z-[100] flex items-center justify-center p-4" style="background:rgba(12,16,20,0.6);backdrop-filter:blur(3px);" role="presentation">
		<div class="modal-card w-full flex flex-col max-h-[90vh] anim-pop" style="max-width:56rem;">
			<div class="flex items-start justify-between gap-4 p-6 border-b border-[color:var(--border)]">
				<div>
					<p class="text-[10px] font-semibold uppercase tracking-wider text-[color:var(--text-muted)]">Detail Work Order Tersimpan</p>
					<h2 class="font-display text-2xl font-bold tracking-wide">{woDetail?.work_order?.wo_number || '—'}</h2>
				</div>
				<div class="flex items-center gap-2">
					{#if woDetail?.work_order}<span class="px-3 py-1 rounded-full text-xs font-bold text-white" style="background:{woStatusColor(woDetail.work_order.wo_status)}">{woDetail.work_order.wo_status}</span>{/if}
					<button class="btn btn-ghost !p-2" aria-label="Tutup" onclick={closeWoDetail}>
						<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2.5"><path d="M6 18L18 6M6 6l12 12" /></svg>
					</button>
				</div>
			</div>

			<div class="p-6 overflow-y-auto" style="max-height:calc(90vh - 110px);">
				{#if woDetailLoading}
					<div class="py-12 text-center text-[color:var(--text-muted)] uppercase tracking-widest text-sm">Memuat detail…</div>
				{:else if woDetail?.work_order}
					<h3 class="font-display text-lg font-bold uppercase tracking-wide mb-3">Data Work Order</h3>
					<div class="grid grid-cols-2 md:grid-cols-3 gap-3 mb-6">
						<div class="panel-flat p-3"><p class="wo-k">Prioritas</p><p class="wo-v">{woDetail.work_order.priority}</p></div>
						<div class="panel-flat p-3"><p class="wo-k">Status Unit (saat dibuat)</p><p class="wo-v">{woDetail.work_order.status_unit}</p></div>
						<div class="panel-flat p-3"><p class="wo-k">Komponen</p><p class="wo-v">{woDetail.work_order.component}</p></div>
						<div class="panel-flat p-3"><p class="wo-k">Part No</p><p class="wo-v">{woDetail.work_order.part_no || '—'}</p></div>
						<div class="panel-flat p-3"><p class="wo-k">RUL (jam)</p><p class="wo-v">{woDetail.work_order.rul_hours}</p></div>
						<div class="panel-flat p-3"><p class="wo-k">Estimasi Biaya</p><p class="wo-v text-amber">{fmtRupiah(woDetail.work_order.est_cost)}</p></div>
						<div class="panel-flat p-3"><p class="wo-k">Teknisi</p><p class="wo-v">{woDetail.work_order.technician || '—'}</p></div>
						<div class="panel-flat p-3"><p class="wo-k">Mulai Perbaikan</p><p class="wo-v text-sm">{woDetail.work_order.scheduled_at ? fmtDateLong(woDetail.work_order.scheduled_at) : '—'}</p></div>
						<div class="panel-flat p-3"><p class="wo-k">Estimasi Selesai</p><p class="wo-v text-sm">{woDetail.work_order.est_completion_at ? fmtDateLong(woDetail.work_order.est_completion_at) : '—'}</p></div>
						<div class="panel-flat p-3"><p class="wo-k">Feedback</p><p class="wo-v">{woDetail.work_order.feedback || '—'}</p></div>
						<div class="panel-flat p-3"><p class="wo-k">Dibuat</p><p class="wo-v text-sm">{fmtDateLong(woDetail.work_order.created_at)}</p></div>
						<div class="panel-flat p-3"><p class="wo-k">Diperbarui</p><p class="wo-v text-sm">{fmtDateLong(woDetail.work_order.updated_at)}</p></div>
					</div>
					{#if woDetail.work_order.notes}
						<div class="panel-flat p-4 mb-6"><p class="wo-k mb-1">Catatan</p><p class="text-sm">{woDetail.work_order.notes}</p></div>
					{/if}

					<h3 class="font-display text-lg font-bold uppercase tracking-wide mb-3">Unit Terkait</h3>
					{#if woDetail.unit}
						<div class="grid grid-cols-2 md:grid-cols-3 gap-3">
							<div class="panel-flat p-3"><p class="wo-k">Kode Unit</p><p class="wo-v">{woDetail.unit.code}</p></div>
							<div class="panel-flat p-3"><p class="wo-k">Jenis Alat Berat</p><p class="wo-v text-sm">{woDetail.unit.jenis_alat_berat_nama || '—'}</p></div>
							<div class="panel-flat p-3"><p class="wo-k">Status Unit Saat Ini</p><p class="wo-v"><span class="px-2 py-0.5 rounded-full text-[11px] font-bold text-white" style="background:{statusColor(woDetail.unit.status)}">{woDetail.unit.status}</span></p></div>
							<div class="panel-flat p-3"><p class="wo-k">Health</p><p class="wo-v">{woDetail.unit.health}%</p></div>
							<div class="panel-flat p-3"><p class="wo-k">Maintenance</p><p class="wo-v text-sm">{woDetail.unit.maintenance}</p></div>
							<div class="panel-flat p-3"><p class="wo-k">Savings</p><p class="wo-v">{fmtRupiahShort(woDetail.unit.savings)}</p></div>
							{#if woDetail.unit.lat && woDetail.unit.lng}<div class="panel-flat p-3"><p class="wo-k">Lokasi</p><p class="wo-v text-sm font-mono">{woDetail.unit.lat.toFixed(4)}, {woDetail.unit.lng.toFixed(4)}</p></div>{/if}
						</div>
						{#if woDetail.unit.lat && woDetail.unit.lng}
							<div class="mt-4">
								<p class="wo-k mb-1.5">Peta Lokasi Unit</p>
								<div id="wo-detail-map" class="w-full rounded-xl overflow-hidden border border-[color:var(--border)] z-0" style="height:16rem;"></div>
							</div>
						{/if}
					{:else}
						<div class="panel-flat p-4 text-sm text-[color:var(--text-muted)]">Unit dengan kode {woDetail.work_order.asset_code} tidak ditemukan di basis data unit.</div>
					{/if}

					<div class="flex justify-end gap-2 mt-6">
						{#if woDetail.work_order.wo_status === 'OPEN'}
							<button class="btn !py-2.5 text-sm border-warning/50 text-warning bg-warning/10" onclick={async () => { await updateWoStatus(woDetail.work_order.id, 'IN_PROGRESS'); openWoDetail(woDetail.work_order.id); }}>Mulai Perbaikan</button>
						{/if}
						{#if woDetail.work_order.wo_status === 'IN_PROGRESS'}
							<button class="btn !py-2.5 text-sm bg-healthy text-white border-healthy font-bold" onclick={async () => { await updateWoStatus(woDetail.work_order.id, 'COMPLETED'); openWoDetail(woDetail.work_order.id); }}>Tandai Selesai (Unit → Sehat)</button>
						{/if}
						<button class="btn btn-ghost !py-2.5 text-sm" onclick={closeWoDetail}>Tutup</button>
					</div>
				{/if}
			</div>
		</div>
	</div>
{/if}

<style>
	.wo-k {
		font-size: 10px;
		text-transform: uppercase;
		letter-spacing: 0.05em;
		color: var(--text-muted, #5d6b7a);
		margin-bottom: 2px;
	}
	.wo-v {
		font-weight: 700;
	}
	.wo-ring {
		--p: 0;
		width: 150px;
		height: 150px;
		border-radius: 50%;
		background: conic-gradient(#f2a60c calc(var(--p) * 1%), var(--surface-2, #e5e8ec) 0);
		display: grid;
		place-items: center;
		transition: background 0.9s linear;
		box-shadow: 0 0 0 1px rgba(242, 166, 12, 0.25), 0 10px 30px -12px rgba(242, 166, 12, 0.4);
		animation: wo-pulse 2.4s ease-in-out infinite;
	}
	.wo-ring-inner {
		width: 116px;
		height: 116px;
		border-radius: 50%;
		background: var(--surface, #fff);
		display: flex;
		flex-direction: column;
		align-items: center;
		justify-content: center;
		gap: 2px;
	}
	@keyframes wo-pulse {
		0%,
		100% {
			box-shadow: 0 0 0 1px rgba(242, 166, 12, 0.25), 0 10px 30px -12px rgba(242, 166, 12, 0.35);
		}
		50% {
			box-shadow: 0 0 0 3px rgba(242, 166, 12, 0.4), 0 14px 40px -10px rgba(242, 166, 12, 0.6);
		}
	}
	.wo-bar {
		height: 12px;
		border-radius: 999px;
		background: var(--surface-2, #e5e8ec);
		overflow: hidden;
	}
	.wo-bar-fill {
		height: 100%;
		border-radius: 999px;
		background: linear-gradient(135deg, #f2a60c 0%, #d9930a 100%);
		transition: width 0.9s linear;
	}
</style>
