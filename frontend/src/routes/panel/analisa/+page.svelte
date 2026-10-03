<script lang="ts">
	import { onMount, onDestroy, tick } from 'svelte';
	import { api } from '$lib/api';
	import { resolveModel } from '$lib/models';
	import { theme } from '$lib/stores/theme.svelte';
	import { pratyaksa } from '$lib/stores/pratyaksa.svelte';

	let overview = $state<any>(null);
	let analysis = $state<any>(null);
	let selectedUnitId = $state<string>('');
	let isLoading = $state(true);
	let error = $state('');
	let autoRefresh = $state(true);
	let lastUpdate = $state('');

	// Unit list pagination
	let unitListPage = $state(1);
	const unitListPerPage = 6;
	const unitListTotalPages = $derived(
		Math.max(1, Math.ceil((overview?.units?.length || 0) / unitListPerPage))
	);
	const pagedUnitList = $derived(
		(overview?.units || []).slice(
			(unitListPage - 1) * unitListPerPage,
			(unitListPage - 1) * unitListPerPage + unitListPerPage
		)
	);

	// Telegram alert engine
	let alertStatus = $state<{ ok: boolean; msg: string } | null>(null);
	let alertTesting = $state(false);
	let alertStatusTimer: ReturnType<typeof setTimeout> | null = null;
	const alertedAssets = new Set<string>();
	const alertCooldown = new Map<string, number>();
	const ALERT_STATUSES = ['CRITICAL', 'WARNING'];

	let refreshTimer: ReturnType<typeof setInterval> | null = null;
	let alertTimer: ReturnType<typeof setInterval> | null = null;
	let ChartLib: any = null;
	const charts: Record<string, any> = {};

	// --- helpers ---
	const riskColor = (level: string) =>
		({ LOW: '#1FA971', MEDIUM: '#E0A106', HIGH: '#E0843E', CRITICAL: '#E0413E' })[level] ||
		'#7A848E';
	const statusColor = (s: string) =>
		({ SEHAT: '#1FA971', WARNING: '#E0A106', CRITICAL: '#E0413E', RUSAK: '#7A848E' })[s] ||
		'#7A848E';
	const rulColor = (l: string) =>
		({ CRITICAL: '#E0413E', WARNING: '#E0A106', NORMAL: '#1FA971', OK: '#1FA971' })[l] ||
		'#7A848E';
	const rulTone = (h: number) => (h < 150 ? '#E0413E' : h < 450 ? '#E0A106' : '#1FA971');
	const rulToneLabel = (h: number) => (h < 150 ? 'CRITICAL' : h < 450 ? 'WARNING' : 'NORMAL');
	const statusLabelColor = (s: string) =>
		({ NORMAL: '#1FA971', WARNING: '#E0A106', CRITICAL: '#E0413E' })[s] || '#7A848E';
	const fmtHours = (h: number) =>
		h == null
			? '-'
			: h >= 24
				? `${Math.floor(h / 24)} hari ${Math.round(h % 24)} jam`
				: `${Math.round(h)} jam`;

	const operationalFields = [
		{ k: 'road_grade_pct', l: 'Road Grade', u: '%' },
		{ k: 'haul_distance_km', l: 'Jarak Angkut', u: ' km' },
		{ k: 'cycle_time_minutes', l: 'Cycle Time', u: ' min' },
		{ k: 'dust_concentration_mgm3', l: 'Konsentrasi Debu', u: ' mg/m³' },
		{ k: 'humidity_pct', l: 'Kelembapan', u: '%' },
		{ k: 'days_since_last_pm', l: 'Hari sejak PM', u: ' hari' },
		{ k: 'last_maintenance_hours', l: 'Jam sejak MTC', u: ' h' },
		{ k: 'fuel_consumption_rate_lph', l: 'Konsumsi BBM', u: ' L/h' },
		{ k: 'boost_pressure_kpa', l: 'Boost Pressure', u: ' kPa' },
		{ k: 'exhaust_gas_temp_c', l: 'Suhu Gas Buang', u: '°C' },
		{ k: 'engine_oil_temp_c', l: 'Suhu Oli Mesin', u: '°C' },
		{ k: 'coolant_pressure_kpa', l: 'Tekanan Coolant', u: ' kPa' },
		{ k: 'vibration_x_g', l: 'Vibrasi X', u: ' g' },
		{ k: 'vibration_y_g', l: 'Vibrasi Y', u: ' g' },
		{ k: 'vibration_z_g', l: 'Vibrasi Z', u: ' g' },
		{ k: 'oil_viscosity_cst', l: 'Viskositas Oli', u: ' cSt' },
		{ k: 'oil_particle_count_iso', l: 'Partikel Oli', u: ' ISO' },
		{ k: 'oil_moisture_pct', l: 'Moisture Oli', u: '%' },
		{ k: 'wear_metal_fe_ppm', l: 'Wear Metal Fe', u: ' ppm' },
		{ k: 'wear_metal_cu_ppm', l: 'Wear Metal Cu', u: ' ppm' }
	];

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
		].sort((a, b) => a.hours - b.hours);
	};

	const lstmComponents = $derived(lstmComponentsOf(analysis));
	const urgentComponents = $derived(lstmComponents.slice(0, 3));
	const digitalTwins = $derived(
		analysis?.prediction?.digital_twin
			? [
					{ label: 'Brake Twin', hours: analysis.prediction.digital_twin.brake_twin_rul },
					{ label: 'Bearing Twin', hours: analysis.prediction.digital_twin.bearing_twin_rul },
					{ label: 'Hydraulic Twin', hours: analysis.prediction.digital_twin.hydraulic_twin_rul }
				]
			: []
	);

	// --- fetch ---
	async function fetchOverview() {
		try {
			const res: any = await api.getAnalisaOverview();
			overview = res.data;
			if (!selectedUnitId && res.data.units?.length > 0) {
				selectedUnitId = res.data.units[0].id;
			}
			error = '';
		} catch (e: any) {
			error = e?.message || 'Gagal memuat data analitik armada.';
		}
	}

	async function fetchAnalysis() {
		if (!selectedUnitId) return;
		try {
			const res: any = await api.getUnitAnalysis(selectedUnitId);
			analysis = res.data;
			lastUpdate = new Date().toLocaleTimeString('id-ID');
		} catch (e: any) {
			error = e?.message || 'Gagal memuat analitik unit.';
		}
	}

	async function refreshAll() {
		await Promise.all([fetchOverview(), fetchAnalysis()]);
		await tick();
		renderAllCharts();
		await maybeSendAlert();
	}

	async function selectUnit(id: string) {
		selectedUnitId = id;
		await fetchAnalysis();
		await tick();
		renderUnitCharts();
	}

	// --- telegram alert ---
	function buildAlertPayload(a: any, statusOverride?: string) {
		const shaps = [...(a.shap_contributions || [])].sort(
			(x: any, y: any) => Math.abs(y.value) - Math.abs(x.value)
		);
		const fmt = (s: any) => (s ? `${s.feature} (${Math.abs(Math.round(s.value))}%)` : '-');
		const urgent = lstmComponentsOf(a)[0];
		const partName = urgent?.label || a.rul_prediction?.component || 'Komponen Utama';
		const code = a.unit?.code || 'unknown';
		const partNo =
			'PRT-' +
			String(code).replace(/[^A-Za-z0-9]/g, '').toUpperCase().slice(0, 6) +
			'-' +
			String(Math.round(urgent?.hours || 0)).padStart(3, '0');
		return {
			asset_id: code,
			model: a.unit?.jenis_alat_berat_nama || '-',
			lokasi: 'Area Tambang Kutai',
			status: statusOverride || a.prediction?.risk_level || 'NORMAL',
			rul: String(Math.round(a.prediction?.lstm_rul_hours || 0)),
			shap1: fmt(shaps[0]),
			shap2: fmt(shaps[1]),
			part_name: partName,
			part_no: partNo,
			stok: String(2 + (String(code).length % 4))
		};
	}

	function showAlertStatus(ok: boolean, msg: string) {
		alertStatus = { ok, msg };
		if (alertStatusTimer) clearTimeout(alertStatusTimer);
		alertStatusTimer = setTimeout(() => (alertStatus = null), 6000);
	}

	async function maybeSendAlert() {
		const ov = overview;
		if (!ov || !Array.isArray(ov.units)) return;
		const atRisk = ov.units.filter((u: any) => ALERT_STATUSES.includes(u.status));
		const atRiskCodes = new Set(atRisk.map((u: any) => u.code));
		for (const code of [...alertedAssets]) {
			if (!atRiskCodes.has(code)) {
				alertedAssets.delete(code);
				alertCooldown.delete(code);
			}
		}
		let sent = 0;
		let failed = 0;
		let lastDetail = '';
		for (const u of atRisk) {
			const asset = u.code;
			if (alertedAssets.has(asset)) continue;
			if (Date.now() < (alertCooldown.get(asset) || 0)) continue;
			try {
				const detail: any = await api.getUnitAnalysis(u.id);
				const a = detail.data;
				await api.sendAlert(buildAlertPayload(a, u.status));
				alertedAssets.add(asset);
				alertCooldown.delete(asset);
				sent++;
			} catch (e: any) {
				alertCooldown.set(asset, Date.now() + 60000);
				failed++;
				lastDetail = e?.message || 'endpoint tak terjangkau';
			}
		}
		if (sent > 0 && failed === 0) {
			showAlertStatus(true, `Alert terkirim untuk ${sent} unit berisiko (CRITICAL/WARNING).`);
		} else if (sent > 0 && failed > 0) {
			showAlertStatus(false, `${sent} alert terkirim, ${failed} gagal: ${lastDetail}`);
		} else if (failed > 0) {
			showAlertStatus(
				false,
				`Gagal kirim alert (${failed} unit): ${lastDetail} — cek koneksi ke endpoint Telegram.`
			);
		}
	}

	async function testTelegram() {
		alertTesting = true;
		try {
			const a = analysis;
			const payload = a
				? { ...buildAlertPayload(a), lokasi: 'Uji Koneksi (TEST)' }
				: {
						asset_id: 'TEST-PING',
						model: 'Pratyaksa Test',
						lokasi: 'Uji Koneksi (TEST)',
						status: 'TEST',
						rul: '0',
						shap1: '-',
						shap2: '-',
						part_name: '-',
						part_no: '-',
						stok: '0'
					};
			const res: any = await api.sendAlert(payload);
			const upMsg = res?.upstream?.message;
			showAlertStatus(
				true,
				`Koneksi Telegram OK — test alert terkirim${a ? ' (' + a.unit.code + ')' : ''}.${upMsg ? ' ' + upMsg : ''}`
			);
		} catch (e: any) {
			showAlertStatus(false, `Test koneksi gagal: ${e?.message || 'endpoint tak terjangkau'}`);
		} finally {
			alertTesting = false;
		}
	}

	// --- charts ---
	function css(v: string) {
		if (typeof window === 'undefined') return '';
		return getComputedStyle(document.documentElement).getPropertyValue(v).trim();
	}
	function themePalette() {
		return {
			tick: css('--text-muted') || '#5d6b7a',
			grid: css('--border') || '#d7dde4',
			axis: css('--border-strong') || '#c2cad3',
			surface: css('--surface') || '#ffffff',
			text: css('--text') || '#1b2128'
		};
	}
	const labelFont = { family: 'Inter', weight: 'bold' as const };
	const monoFont = { family: 'JetBrains Mono' };

	const arcValueLabel = {
		id: 'arcValueLabel',
		afterDatasetsDraw(chart: any) {
			const { ctx } = chart;
			const meta = chart.getDatasetMeta(0);
			const ds = chart.data.datasets[0];
			if (!meta || !meta.data) return;
			meta.data.forEach((arc: any, i: number) => {
				const val = ds.data[i];
				if (val == null || val === 0) return;
				const pos = arc.tooltipPosition();
				ctx.save();
				ctx.font = '800 14px Inter, sans-serif';
				ctx.textAlign = 'center';
				ctx.textBaseline = 'middle';
				ctx.shadowColor = 'rgba(0,0,0,0.55)';
				ctx.shadowBlur = 4;
				ctx.fillStyle = '#ffffff';
				ctx.fillText(String(val), pos.x, pos.y);
				ctx.restore();
			});
		}
	};
	const barValueLabel = {
		id: 'barValueLabel',
		afterDatasetsDraw(chart: any) {
			const { ctx } = chart;
			const meta = chart.getDatasetMeta(0);
			const ds = chart.data.datasets[0];
			if (!meta || !meta.data) return;
			const tickColor = css('--text') || '#1b2128';
			meta.data.forEach((bar: any, i: number) => {
				const val = ds.data[i];
				if (val == null) return;
				ctx.save();
				ctx.font = '800 13px JetBrains Mono, monospace';
				ctx.textAlign = 'center';
				ctx.textBaseline = 'bottom';
				ctx.fillStyle = tickColor;
				ctx.fillText(String(val), bar.x, bar.y - 6);
				ctx.restore();
			});
		}
	};
	const barValueLabelH = {
		id: 'barValueLabelH',
		afterDatasetsDraw(chart: any) {
			const { ctx } = chart;
			const meta = chart.getDatasetMeta(0);
			const ds = chart.data.datasets[0];
			if (!meta || !meta.data) return;
			const col = css('--text-muted') || '#5d6b7a';
			meta.data.forEach((bar: any, i: number) => {
				const val = ds.data[i];
				if (val == null) return;
				ctx.save();
				ctx.font = '700 10px JetBrains Mono, monospace';
				ctx.textAlign = 'left';
				ctx.textBaseline = 'middle';
				ctx.fillStyle = col;
				ctx.fillText(`${val}j`, bar.x + 6, bar.y);
				ctx.restore();
			});
		}
	};

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

	function renderOverviewCharts() {
		if (!overview) return;
		const t = themePalette();
		const sd = overview.status_distribution;
		upsertChart('statusPie', 'statusPie', {
			type: 'doughnut',
			data: {
				labels: sd.map((s: any) => s.label),
				datasets: [
					{
						data: sd.map((s: any) => s.count),
						backgroundColor: sd.map((s: any) => statusColor(s.label)),
						borderColor: t.surface,
						borderWidth: 3
					}
				]
			},
			plugins: [arcValueLabel],
			options: {
				responsive: true,
				maintainAspectRatio: false,
				cutout: '60%',
				plugins: {
					legend: {
						position: 'bottom',
						labels: { font: labelFont, color: t.tick, boxWidth: 12, usePointStyle: true }
					}
				}
			}
		});

		const rd = overview.risk_distribution;
		upsertChart('riskBar', 'riskBar', {
			type: 'bar',
			data: {
				labels: rd.map((r: any) => r.label),
				datasets: [
					{
						data: rd.map((r: any) => r.count),
						backgroundColor: rd.map((r: any) => riskColor(r.label)),
						borderRadius: 6,
						borderSkipped: false
					}
				]
			},
			plugins: [barValueLabel],
			options: {
				responsive: true,
				maintainAspectRatio: false,
				plugins: { legend: { display: false } },
				scales: {
					x: {
						ticks: { font: labelFont, color: t.tick },
						grid: { display: false },
						border: { color: t.axis }
					},
					y: {
						beginAtZero: true,
						ticks: { font: monoFont, color: t.tick, stepSize: 1 },
						grid: { color: t.grid },
						border: { color: t.axis }
					}
				}
			}
		});
	}

	function renderUnitCharts() {
		if (!analysis) return;
		const t = themePalette();

		const rs = analysis.risk_score;
		upsertChart('riskGauge', 'riskGauge', {
			type: 'doughnut',
			data: {
				labels: ['Risk', 'Sisa'],
				datasets: [
					{
						data: [rs, 100 - rs],
						backgroundColor: [riskColor(analysis.risk_level), t.grid],
						borderColor: t.surface,
						borderWidth: 2,
						circumference: 180,
						rotation: 270
					}
				]
			},
			options: {
				responsive: true,
				maintainAspectRatio: false,
				cutout: '72%',
				plugins: { legend: { display: false }, tooltip: { enabled: false } }
			}
		});

		const ch = analysis.component_health;
		upsertChart('radar', 'radar', {
			type: 'radar',
			data: {
				labels: ch.map((c: any) => c.component),
				datasets: [
					{
						label: 'Health Score',
						data: ch.map((c: any) => c.health),
						backgroundColor: 'rgba(62,146,204,0.18)',
						borderColor: '#3E92CC',
						borderWidth: 2.5,
						pointBackgroundColor: '#3E92CC',
						pointBorderColor: t.surface,
						pointRadius: 4
					}
				]
			},
			options: {
				responsive: true,
				maintainAspectRatio: false,
				plugins: { legend: { display: false } },
				scales: {
					r: {
						min: 0,
						max: 100,
						ticks: {
							stepSize: 25,
							font: { family: 'JetBrains Mono', size: 9 },
							color: t.tick,
							backdropColor: 'transparent'
						},
						grid: { color: t.grid },
						angleLines: { color: t.grid },
						pointLabels: { font: labelFont, color: t.text }
					}
				}
			}
		});

		const hist = analysis.sensor_history;
		upsertChart('history', 'history', {
			type: 'line',
			data: {
				labels: hist.map((h: any) => h.time),
				datasets: [
					{ label: 'Suhu (°C)', data: hist.map((h: any) => h.suhu_mesin), borderColor: '#E0413E', backgroundColor: '#E0413E', borderWidth: 2, pointRadius: 0, tension: 0.35, yAxisID: 'y' },
					{ label: 'Akustik (dB)', data: hist.map((h: any) => h.acoustic), borderColor: '#E0843E', backgroundColor: '#E0843E', borderWidth: 2, pointRadius: 0, tension: 0.35, yAxisID: 'y' },
					{ label: 'Vibrasi (g)', data: hist.map((h: any) => h.vibration), borderColor: '#3E92CC', backgroundColor: '#3E92CC', borderWidth: 2, pointRadius: 0, tension: 0.35, yAxisID: 'y1' },
					{ label: 'Tekanan Oli (bar)', data: hist.map((h: any) => h.tekanan_oli), borderColor: '#1FA971', backgroundColor: '#1FA971', borderWidth: 2, pointRadius: 0, tension: 0.35, yAxisID: 'y1' }
				]
			},
			options: {
				responsive: true,
				maintainAspectRatio: false,
				interaction: { mode: 'index', intersect: false },
				plugins: {
					legend: {
						position: 'bottom',
						labels: { font: { family: 'Inter', size: 10, weight: 'bold' }, color: t.tick, boxWidth: 12, usePointStyle: true }
					}
				},
				scales: {
					x: { ticks: { font: { family: 'JetBrains Mono', size: 9 }, color: t.tick, maxTicksLimit: 8 }, grid: { display: false }, border: { color: t.axis } },
					y: { position: 'left', ticks: { font: { family: 'JetBrains Mono', size: 9 }, color: t.tick }, grid: { color: t.grid }, border: { color: t.axis } },
					y1: { position: 'right', ticks: { font: { family: 'JetBrains Mono', size: 9 }, color: t.tick }, grid: { display: false }, border: { color: t.axis } }
				}
			}
		});

		const shap = [...(analysis.shap_contributions || [])].sort(
			(a: any, b: any) => Math.abs(b.value) - Math.abs(a.value)
		);
		upsertChart('shap', 'shap', {
			type: 'bar',
			data: {
				labels: shap.map((s: any) => s.feature),
				datasets: [
					{
						data: shap.map((s: any) => s.value),
						backgroundColor: shap.map((s: any) => (s.value >= 0 ? '#E0413E' : '#1FA971')),
						borderRadius: 5,
						borderSkipped: false
					}
				]
			},
			options: {
				indexAxis: 'y',
				responsive: true,
				maintainAspectRatio: false,
				plugins: {
					legend: { display: false },
					tooltip: { callbacks: { label: (c: any) => `${c.raw >= 0 ? '+' : ''}${c.raw} ke risiko` } }
				},
				scales: {
					x: { ticks: { font: { family: 'JetBrains Mono', size: 9 }, color: t.tick }, grid: { color: t.grid }, border: { color: t.axis } },
					y: { ticks: { font: { family: 'Inter', size: 10, weight: 'bold' }, color: t.text }, grid: { display: false }, border: { color: t.axis } }
				}
			}
		});

		const tm = analysis.telemetry;
		upsertChart('labMetals', 'labMetals', {
			type: 'bar',
			data: {
				labels: ['Fe (Besi)', 'Cu (Tembaga)', 'Al (Aluminium)', 'Si (Silika)'],
				datasets: [
					{
						label: 'ppm',
						data: [tm.lab_fe_ppm, tm.lab_cu_ppm, tm.lab_al_ppm, tm.lab_si_ppm],
						backgroundColor: ['#E0413E', '#E0843E', '#3E92CC', '#9B7BE0'],
						borderRadius: 5,
						borderSkipped: false
					}
				]
			},
			options: {
				responsive: true,
				maintainAspectRatio: false,
				plugins: { legend: { display: false } },
				scales: {
					x: { ticks: { font: { family: 'Inter', size: 9, weight: 'bold' }, color: t.tick }, grid: { display: false }, border: { color: t.axis } },
					y: { beginAtZero: true, ticks: { font: { family: 'JetBrains Mono', size: 9 }, color: t.tick }, grid: { color: t.grid }, border: { color: t.axis } }
				}
			}
		});

		const rc = lstmComponents;
		upsertChart('rulComponents', 'rulComponents', {
			type: 'bar',
			data: {
				labels: rc.map((c: any) => c.label),
				datasets: [
					{
						data: rc.map((c: any) => c.hours),
						backgroundColor: rc.map((c: any) => rulTone(c.hours)),
						borderRadius: 5,
						borderSkipped: false
					}
				]
			},
			plugins: [barValueLabelH],
			options: {
				indexAxis: 'y',
				responsive: true,
				maintainAspectRatio: false,
				layout: { padding: { right: 40 } },
				plugins: {
					legend: { display: false },
					tooltip: { callbacks: { label: (c: any) => `${c.raw} jam tersisa` } }
				},
				scales: {
					x: { beginAtZero: true, ticks: { font: { family: 'JetBrains Mono', size: 9 }, color: t.tick }, grid: { color: t.grid }, border: { color: t.axis } },
					y: { ticks: { font: { family: 'Inter', size: 10, weight: 'bold' }, color: t.text }, grid: { display: false }, border: { color: t.axis } }
				}
			}
		});
	}

	function renderAllCharts() {
		renderOverviewCharts();
		renderUnitCharts();
	}

	onMount(async () => {
		isLoading = true;
		const mod = await import('chart.js/auto');
		ChartLib = mod.default;
		await fetchOverview();
		await fetchAnalysis();
		isLoading = false;
		await tick();
		renderAllCharts();

		pratyaksa.fetchAll();
		pratyaksa.startPolling(10000);

		refreshTimer = setInterval(() => {
			if (autoRefresh) refreshAll();
		}, 15000);

		alertTimer = setInterval(() => {
			maybeSendAlert();
		}, 5000);
	});

	onDestroy(() => {
		if (refreshTimer) clearInterval(refreshTimer);
		if (alertTimer) clearInterval(alertTimer);
		if (alertStatusTimer) clearTimeout(alertStatusTimer);
		pratyaksa.stopPolling();
		Object.values(charts).forEach((c) => c?.destroy());
	});

	// Re-render charts when theme toggles.
	$effect(() => {
		theme.isDark;
		tick().then(() => {
			if (ChartLib) renderAllCharts();
		});
	});
</script>

<svelte:head><title>Analisa Kerusakan — Pratyaksa</title></svelte:head>

<header class="flex justify-between items-start mb-8 flex-wrap gap-4">
	<div>
		<h1 class="font-display text-4xl md:text-5xl font-bold uppercase tracking-wide leading-none">Analisa Kerusakan</h1>
		<p class="mt-2 text-[color:var(--text-muted)]">Monitoring kondisi &amp; prediksi kegagalan armada secara real-time.</p>
	</div>
	<div class="flex items-center gap-3">
		<button
			class="flex items-center gap-2 px-3 py-2 rounded-xl text-xs font-semibold border border-[color:var(--border)] text-[color:var(--text-muted)] hover:bg-[color:var(--surface-2)] transition-all disabled:opacity-60"
			disabled={alertTesting}
			onclick={testTelegram}
		>
			<svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2"
				><path stroke-linecap="round" stroke-linejoin="round" d="M8.29 6.293a9 9 0 1111.418 11.418M12 2a10 10 0 019.95 9M2 12h2m2-6-2-2m14 14l2 2M12 20v2m-4-2l-2 2" /></svg
			>
			{alertTesting ? 'Mengirim…' : 'Test Telegram'}
		</button>
		<div class="panel-flat px-3 py-2 text-[10px] font-mono text-[color:var(--text-muted)]">
			Update<br /><span class="font-semibold text-[color:var(--text)]">{lastUpdate || '—'}</span>
		</div>
	</div>
</header>

{#if alertStatus}
	<div
		class="mb-4 px-4 py-2.5 rounded-xl text-sm font-semibold flex items-center gap-2 {alertStatus.ok
			? 'bg-healthy/10 border border-healthy/40 text-healthy'
			: 'bg-critical/10 border border-critical/40 text-critical'}"
	>
		<svg class="w-4 h-4 shrink-0" fill="currentColor" viewBox="0 0 24 24"
			><path d="M9.78 18.65l.28-4.23 7.68-6.92c.34-.31-.07-.46-.52-.19L7.74 13.3 3.64 12c-.88-.25-.89-.86.2-1.3l15.97-6.16c.73-.33 1.43.18 1.15 1.3l-2.72 12.81c-.19.91-.74 1.13-1.5.71L12.6 16.3l-1.99 1.93c-.23.23-.42.42-.83.42z" /></svg
		>
		{alertStatus.msg}
	</div>
{/if}

{#if error}<div class="mb-6 px-4 py-3 rounded-xl bg-critical/10 border border-critical/40 text-critical font-semibold">⚠️ {error}</div>{/if}

{#if isLoading}
	<div class="flex items-center justify-center h-96 font-semibold text-[color:var(--text-faint)] uppercase tracking-widest">Memuat analitik…</div>
{:else if overview}
	<!-- KPI Cards -->
	<div class="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-7">
		<div class="kpi anim-pop d-1 p-5" style="--accent:#3E92CC"><p class="text-[10px] font-semibold uppercase tracking-wider text-[color:var(--text-muted)] mb-1">Total Unit</p><p class="font-display text-4xl font-bold">{overview.total_units}</p></div>
		<div class="kpi anim-pop d-2 p-5" style="--accent:#1FA971"><p class="text-[10px] font-semibold uppercase tracking-wider text-[color:var(--text-muted)] mb-1">Rata-rata Health</p><p class="font-display text-4xl font-bold text-healthy">{overview.avg_health}%</p></div>
		<div class="kpi anim-pop d-3 p-5" style="--accent:#E0A106"><p class="text-[10px] font-semibold uppercase tracking-wider text-[color:var(--text-muted)] mb-1">Rata-rata Risk</p><p class="font-display text-4xl font-bold text-warning">{overview.avg_risk_score}</p></div>
		<div class="kpi anim-pop d-4 p-5 {overview.units_at_risk > 0 ? 'anim-glow' : ''}" style="--accent:#E0413E"><p class="text-[10px] font-semibold uppercase tracking-wider text-[color:var(--text-muted)] mb-1">Unit Berisiko</p><p class="font-display text-4xl font-bold text-critical">{overview.units_at_risk}</p></div>
	</div>

	<!-- Fleet charts -->
	<div class="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-7">
		<div class="panel p-6 anim-up d-2"><h2 class="font-display text-xl font-bold uppercase tracking-wide mb-4 pb-2 border-b border-[color:var(--border)]">Distribusi Status Armada</h2><div style="height:256px;"><canvas id="statusPie"></canvas></div></div>
		<div class="panel p-6 anim-up d-3"><h2 class="font-display text-xl font-bold uppercase tracking-wide mb-4 pb-2 border-b border-[color:var(--border)]">Distribusi Tingkat Risiko</h2><div style="height:256px;"><canvas id="riskBar"></canvas></div></div>
	</div>

	<!-- Unit list + detail -->
	<div class="grid grid-cols-1 lg:grid-cols-4 gap-6 items-start">
		<!-- Unit list -->
		<div class="lg:col-span-1 panel p-4 lg:sticky lg:top-0">
			<h2 class="font-display text-lg font-bold uppercase tracking-wide mb-4 pb-2 border-b border-[color:var(--border)]">Pilih Unit</h2>
			<div class="space-y-2">
				{#each pagedUnitList as u (u.id)}
					<button
						class="w-full text-left p-3 rounded-lg border transition-all {selectedUnitId === u.id ? 'border-amber bg-amber/10' : 'border-[color:var(--border)] hover:border-steel hover:bg-[color:var(--surface-2)]'}"
						onclick={() => selectUnit(u.id)}
					>
						<div class="flex justify-between items-center">
							<span class="font-mono font-semibold text-sm">{u.code}</span>
							<span class="px-2 py-0.5 rounded-full text-[9px] font-bold text-white" style="background-color:{riskColor(u.risk_level)}">{u.risk_level}</span>
						</div>
						<div class="flex justify-between items-center mt-1.5">
							<span class="text-[11px] text-[color:var(--text-muted)] truncate">{u.jenis_alat_berat_nama}</span>
							<span class="text-[11px] font-mono font-semibold">Risk {u.risk_score}</span>
						</div>
					</button>
				{/each}
			</div>
			{#if unitListTotalPages > 1}
				<div class="flex items-center justify-between mt-3 pt-3 border-t border-[color:var(--border)]">
					<span class="text-[11px] font-medium text-[color:var(--text-faint)]">Hal {unitListPage} / {unitListTotalPages}</span>
					<div class="flex gap-1.5">
						<button class="mini-pg" disabled={unitListPage === 1} onclick={() => (unitListPage = Math.max(1, unitListPage - 1))}>‹</button>
						<button class="mini-pg" disabled={unitListPage === unitListTotalPages} onclick={() => (unitListPage = Math.min(unitListTotalPages, unitListPage + 1))}>›</button>
					</div>
				</div>
			{/if}
		</div>

		<!-- Detail -->
		{#if analysis}
			<div class="lg:col-span-3 space-y-6">
				<!-- Header unit -->
				<div class="rounded-xl bg-steel-gradient text-white p-5 flex justify-between items-center flex-wrap gap-3">
					<div>
						<p class="text-amber font-mono font-semibold text-xs">{analysis.unit.code}</p>
						<p class="font-display font-bold text-xl uppercase tracking-wide">{analysis.unit.jenis_alat_berat_nama}</p>
					</div>
					<div class="flex gap-4 items-center">
						<div class="text-center"><p class="text-[9px] text-graphite-300 uppercase tracking-wider">Health</p><p class="text-2xl font-display font-bold">{analysis.unit.health}%</p></div>
						<div class="px-3 py-2 rounded-lg text-white font-bold text-sm" style="background-color:{riskColor(analysis.risk_level)}">{analysis.risk_level}</div>
					</div>
				</div>

				<!-- 3D + Gauge + Radar -->
				<div class="grid grid-cols-1 md:grid-cols-3 gap-6">
					<div class="panel p-6 anim-up d-1">
						<h3 class="font-display text-lg font-bold uppercase tracking-wide mb-3 pb-2 border-b border-[color:var(--border)]">Visual 3D Unit</h3>
						<div class="rounded-xl border border-[color:var(--border)] bg-steel-gradient relative overflow-hidden h-48">
							<model-viewer src={resolveModel(analysis.unit.model3d_url, analysis.unit.jenis_alat_berat_nama)} alt="Model 3D unit alat berat" camera-controls auto-rotate auto-rotate-delay="0" rotation-per-second="35deg" shadow-intensity="1.4" exposure="1.1" environment-image="neutral" interaction-prompt="none" style="width:100%;height:100%;outline:none;background-color:transparent;"></model-viewer>
							<div class="absolute top-2 left-2 bg-steel/90 text-white text-[8px] font-semibold px-2 py-0.5 rounded-full pointer-events-none">● LIVE 3D</div>
							<div class="absolute bottom-2 right-2 bg-graphite-900/80 text-graphite-100 text-[8px] font-medium px-2 py-0.5 rounded-full pointer-events-none">DRAG 360°</div>
						</div>
					</div>
					<div class="panel p-6">
						<h3 class="font-display text-lg font-bold uppercase tracking-wide mb-3 pb-2 border-b border-[color:var(--border)]">Risk Score</h3>
						<div class="h-48 relative">
							<canvas id="riskGauge"></canvas>
							<div class="absolute inset-0 flex flex-col items-center justify-end pb-2 pointer-events-none">
								<span class="text-5xl font-display font-bold">{analysis.risk_score}</span>
								<span class="text-xs text-[color:var(--text-muted)] uppercase tracking-wider">/ 100</span>
							</div>
						</div>
					</div>
					<div class="panel p-6">
						<h3 class="font-display text-lg font-bold uppercase tracking-wide mb-3 pb-2 border-b border-[color:var(--border)]">Kesehatan Komponen</h3>
						<div class="h-48"><canvas id="radar"></canvas></div>
					</div>
				</div>

				<!-- Sensor readings -->
				<div class="panel p-6">
					<h3 class="font-display text-lg font-bold uppercase tracking-wide mb-4 pb-2 border-b border-[color:var(--border)]">Telemetri Sensor Real-Time</h3>
					<div class="grid grid-cols-2 md:grid-cols-4 gap-3">
						{#each [
							{ label: 'Suhu Mesin', val: analysis.sensor_readings.suhu_mesin + '°C', danger: analysis.sensor_readings.suhu_mesin > 105 },
							{ label: 'Vibrasi', val: analysis.sensor_readings.vibration + ' g', danger: analysis.sensor_readings.vibration > 6 },
							{ label: 'Tekanan Oli', val: analysis.sensor_readings.tekanan_oli + ' bar', danger: analysis.sensor_readings.tekanan_oli < 3 },
							{ label: 'RPM', val: analysis.sensor_readings.rpm, danger: false },
							{ label: 'Fuel Level', val: analysis.sensor_readings.fuel_level + '%', danger: analysis.sensor_readings.fuel_level < 20 },
							{ label: 'Partikel Oli', val: 'ISO ' + analysis.sensor_readings.oil_particle_iso, danger: analysis.sensor_readings.oil_particle_iso > 19 },
							{ label: 'Emisi Akustik', val: analysis.sensor_readings.acoustic_db + ' dB', danger: analysis.sensor_readings.acoustic_db > 90 },
							{ label: 'Jam Operasi', val: analysis.sensor_readings.jam_operasi + ' h', danger: false }
						] as s (s.label)}
							<div class={s.danger ? 'cell cell-danger' : 'cell'}>
								<p class="cell-label">{s.label}</p>
								<p class="cell-val text-lg">{s.val}</p>
							</div>
						{/each}
					</div>
				</div>

				<!-- Time-series -->
				<div class="panel p-6">
					<h3 class="font-display text-lg font-bold uppercase tracking-wide mb-4 pb-2 border-b border-[color:var(--border)]">Tren Sensor 24 Jam Terakhir</h3>
					<div style="height:288px;"><canvas id="history"></canvas></div>
				</div>

				<!-- Telemetri lengkap -->
				<div class="panel p-6">
					<div class="flex justify-between items-center mb-4 pb-2 border-b border-[color:var(--border)] flex-wrap gap-2">
						<h3 class="font-display text-lg font-bold uppercase tracking-wide">Telemetri On-Board (VIMS / KOMTRAX)</h3>
						<span class="badge text-white" style="background-color:{statusLabelColor(analysis.telemetry.status_label)};border-color:{statusLabelColor(analysis.telemetry.status_label)}">STATUS: {analysis.telemetry.status_label}</span>
					</div>

					<p class="text-[10px] font-semibold uppercase tracking-wider text-[color:var(--text-faint)] mb-2">⚙️ ECM / VIMS — Sensor Fisik</p>
					<div class="grid grid-cols-2 md:grid-cols-4 gap-3 mb-6">
						{#each [
							{ l: 'Eng Coolant', v: analysis.telemetry.eng_coolant_temp_c + '°C', d: analysis.telemetry.eng_coolant_temp_c > 110 },
							{ l: 'Eng Oil Press', v: analysis.telemetry.eng_oil_press_psi + ' PSI', d: analysis.telemetry.eng_oil_press_psi < 25 },
							{ l: 'Eng RPM', v: analysis.telemetry.eng_rpm, d: false },
							{ l: 'Eng Load', v: analysis.telemetry.eng_load_pct + '%', d: false },
							{ l: 'Hyd Pump Press', v: analysis.telemetry.hyd_pump_press_psi + ' PSI', d: false },
							{ l: 'Hyd Oil Temp', v: analysis.telemetry.hyd_oil_temp_c + '°C', d: analysis.telemetry.hyd_oil_temp_c > 100 },
							{ l: 'Trans Oil Temp', v: analysis.telemetry.trans_oil_temp_c + '°C', d: analysis.telemetry.trans_oil_temp_c > 110 },
							{ l: 'Torque Conv Temp', v: analysis.telemetry.torque_converter_temp_c + '°C', d: analysis.telemetry.torque_converter_temp_c > 115 },
							{ l: 'Final Drive Temp', v: analysis.telemetry.final_drive_temp_c + '°C', d: analysis.telemetry.final_drive_temp_c > 105 },
							{ l: 'Brake Cooling', v: analysis.telemetry.brake_cooling_temp_c + '°C', d: analysis.telemetry.brake_cooling_temp_c > 95 },
							{ l: 'Battery', v: analysis.telemetry.battery_voltage + ' V', d: analysis.telemetry.battery_voltage < 23 },
							{ l: 'Idle Ratio', v: (analysis.telemetry.idle_time_ratio * 100).toFixed(0) + '%', d: false }
						] as s (s.l)}
							<div class={s.d ? 'cell cell-danger' : 'cell'}>
								<p class="cell-label">{s.l}</p>
								<p class="cell-val text-base">{s.v}</p>
							</div>
						{/each}
					</div>

					<!-- FMS + CMMS + LIMS -->
					<div class="grid grid-cols-1 md:grid-cols-2 gap-6 mb-6">
						<div>
							<p class="text-[10px] font-semibold uppercase tracking-wider text-[color:var(--text-faint)] mb-2">🚚 FMS / Dispatch &amp; 🔧 CMMS</p>
							<div class="grid grid-cols-2 gap-3">
								<div class="cell !text-left"><p class="cell-label">Component Type</p><p class="cell-val text-sm">{analysis.telemetry.component_type}</p></div>
								<div class="cell !text-left"><p class="cell-label">Operator</p><p class="cell-val text-sm">{analysis.telemetry.operator_id}</p></div>
								<div class="cell !text-left"><p class="cell-label">Payload</p><p class="cell-val text-sm">{analysis.telemetry.payload_tonnage} t</p></div>
								<div class="cell !text-left"><p class="cell-label">Ambient Temp</p><p class="cell-val text-sm">{analysis.telemetry.ambient_temp_c}°C</p></div>
								<div class="cell !text-left"><p class="cell-label">Hour Meter</p><p class="cell-val text-sm">{analysis.telemetry.hour_meter_actual.toLocaleString()} HM</p></div>
								<div class="cell !text-left"><p class="cell-label">Design Life</p><p class="cell-val text-sm">{analysis.telemetry.design_life_hm.toLocaleString()} HM</p></div>
								<div class="cell !text-left"><p class="cell-label">Component Age</p><p class="cell-val text-sm">{analysis.telemetry.component_age_hm.toLocaleString()} HM</p></div>
								<div class="cell !text-left"><p class="cell-label">Remanufactured</p><p class="cell-val text-sm">{analysis.telemetry.is_remanufactured ? 'YA' : 'TIDAK'}</p></div>
								<div class="!text-left col-span-2 rounded-[10px] p-2.5 border {analysis.telemetry.fault_code_severity >= 3 ? 'cell-danger' : analysis.telemetry.fault_code_severity >= 2 ? 'cell-warn' : 'cell'}">
									<p class="cell-label">Fault Code Severity (DTC)</p>
									<p class="cell-val text-sm">Level {analysis.telemetry.fault_code_severity} / 4</p>
								</div>
							</div>
						</div>

						<!-- LIMS -->
						<div>
							<p class="text-[10px] font-semibold uppercase tracking-wider text-[color:var(--text-faint)] mb-2">🧪 LIMS — Analisis Pelumas</p>
							<div style="height:160px;" class="mb-3"><canvas id="labMetals"></canvas></div>
							<div class="grid grid-cols-3 gap-2">
								<div class="cell"><p class="cell-label">Viskositas 100C</p><p class="cell-val text-sm">{analysis.telemetry.lab_viscosity_100c}</p></div>
								<div class={analysis.telemetry.lab_water_content_pct > 0.5 ? 'cell cell-danger' : 'cell'}><p class="cell-label">Water %</p><p class="cell-val text-sm">{analysis.telemetry.lab_water_content_pct}</p></div>
								<div class={analysis.telemetry.lab_soot_pct > 3 ? 'cell cell-warn' : 'cell'}><p class="cell-label">Soot %</p><p class="cell-val text-sm">{analysis.telemetry.lab_soot_pct}</p></div>
							</div>
						</div>
					</div>

					<!-- Engineer generated -->
					<p class="text-[10px] font-semibold uppercase tracking-wider text-[color:var(--text-faint)] mb-2">🧮 Engineer Generated Features</p>
					<div class="grid grid-cols-3 gap-3">
						<div class="rounded-[10px] p-3 text-center text-white" style="background:#3E92CC"><p class="text-[9px] font-semibold uppercase tracking-wider text-white/80">Delta Eng Temp</p><p class="text-xl font-display font-bold">{analysis.telemetry.delta_eng_temp}°C</p></div>
						<div class="rounded-[10px] p-3 text-center text-white" style="background-color:{statusLabelColor(analysis.telemetry.status_label)}"><p class="text-[9px] font-semibold uppercase tracking-wider text-white/80">Status Label</p><p class="text-xl font-display font-bold">{analysis.telemetry.status_label}</p></div>
						<div class="rounded-[10px] p-3 text-center bg-steel-gradient text-white"><p class="text-[9px] font-semibold uppercase tracking-wider text-graphite-300">RUL (Telemetri)</p><p class="text-xl font-display font-bold text-amber">{fmtHours(analysis.telemetry.rul_hours)}</p></div>
					</div>
				</div>

				<!-- Prediksi AI — XGBoost + LSTM + Digital Twin -->
				<div class="panel p-6">
					<div class="flex justify-between items-center mb-4 pb-2 border-b border-[color:var(--border)] flex-wrap gap-2">
						<h3 class="font-display text-lg font-bold uppercase tracking-wide">Prediksi AI — Anomali &amp; RUL</h3>
						<div class="flex items-center gap-2 flex-wrap">
							<span class="badge {analysis.prediction.model_agreement ? 'bg-healthy/15 border-healthy/40 text-healthy' : 'bg-warning/15 border-warning/40 text-warning'}">{analysis.prediction.model_agreement ? 'Model Sepakat' : 'Model Konflik'}</span>
							<span class="text-[10px] font-mono text-[color:var(--text-faint)]">{analysis.prediction.equipment_type} · {analysis.prediction.latency_ms}ms</span>
						</div>
					</div>

					<div class="grid grid-cols-1 md:grid-cols-4 gap-3 mb-5">
						<div class="rounded-xl p-4 border" style="border-color:{rulColor(analysis.prediction.xgb_anomaly_label)}55;background:{rulColor(analysis.prediction.xgb_anomaly_label)}12">
							<p class="cell-label">XGBoost Anomaly</p>
							<p class="font-display text-2xl font-bold mt-0.5" style="color:{rulColor(analysis.prediction.xgb_anomaly_label)}">{analysis.prediction.xgb_anomaly_label}</p>
							<p class="text-[11px] text-[color:var(--text-faint)] mt-0.5">Kelas {analysis.prediction.xgb_anomaly_class} / 2</p>
						</div>
						<div class="rounded-xl p-4 border border-[color:var(--border)] bg-[color:var(--surface-2)]">
							<p class="cell-label">LSTM RUL (Sistem)</p>
							<p class="font-display text-2xl font-bold mt-0.5">{analysis.prediction.lstm_rul_hours} <span class="text-sm font-normal text-[color:var(--text-muted)]">jam</span></p>
							<p class="text-[11px] text-[color:var(--text-faint)] mt-0.5">± {analysis.prediction.rul_uncertainty} jam (uncertainty)</p>
						</div>
						<div class="rounded-xl p-4 border" style="border-color:{rulColor(analysis.prediction.risk_level)}55;background:{rulColor(analysis.prediction.risk_level)}12">
							<p class="cell-label">Risk Level (Final)</p>
							<p class="font-display text-2xl font-bold mt-0.5" style="color:{rulColor(analysis.prediction.risk_level)}">{analysis.prediction.risk_level}</p>
							<p class="text-[11px] text-[color:var(--text-faint)] mt-0.5">Kelas {analysis.prediction.risk_class} / 2</p>
						</div>
						<div class="rounded-xl p-4 border {analysis.prediction.drift_status.drift_detected ? 'border-warning/40 bg-warning/10' : 'border-[color:var(--border)] bg-[color:var(--surface-2)]'}">
							<p class="cell-label">Feature Drift</p>
							<p class="font-display text-2xl font-bold mt-0.5 {analysis.prediction.drift_status.drift_detected ? 'text-warning' : 'text-healthy'}">{analysis.prediction.drift_status.drift_detected ? 'TERDETEKSI' : 'STABIL'}</p>
							<p class="text-[11px] text-[color:var(--text-faint)] mt-0.5">z-max {analysis.prediction.drift_status.max_z_score} · {analysis.prediction.drift_status.n_drifted} fitur</p>
						</div>
					</div>

					<div class="grid grid-cols-1 sm:grid-cols-3 gap-3 mb-5">
						{#each urgentComponents as c (c.label)}
							<div class="rounded-xl p-4 border" style="border-color:{rulTone(c.hours)}66;background:{rulTone(c.hours)}14">
								<div class="flex items-center justify-between mb-1"><span class="text-[10px] font-bold uppercase tracking-wide" style="color:{rulTone(c.hours)}">{rulToneLabel(c.hours)}</span></div>
								<p class="font-semibold text-sm leading-tight">{c.label}</p>
								<p class="font-display text-2xl font-bold mt-1" style="color:{rulTone(c.hours)}">{fmtHours(c.hours)}</p>
							</div>
						{/each}
					</div>

					<p class="text-[10px] font-semibold uppercase tracking-wider text-[color:var(--text-faint)] mb-2">RUL per Komponen (LSTM)</p>
					<div style="height:288px;"><canvas id="rulComponents"></canvas></div>

					<p class="text-[10px] font-semibold uppercase tracking-wider text-[color:var(--text-faint)] mt-5 mb-2">Digital Twin (Physics-based)</p>
					<div class="grid grid-cols-3 gap-3">
						{#each digitalTwins as d (d.label)}
							<div class="cell"><p class="cell-label">{d.label}</p><p class="cell-val text-lg" style="color:{rulTone(d.hours)}">{d.hours} <span class="text-xs font-normal">jam</span></p></div>
						{/each}
					</div>

					{#if analysis.prediction.drift_status.drift_detected}
						<div class="mt-4 px-4 py-3 rounded-lg bg-warning/10 border border-warning/40">
							<span class="font-semibold text-warning text-sm">⚠ Fitur ter-drift:</span>
							<span class="font-mono text-xs text-[color:var(--text-muted)] ml-1">{analysis.prediction.drift_status.drifted_features.join(', ')}</span>
						</div>
					{/if}
				</div>

				<!-- Parameter Operasional & Lingkungan -->
				<div class="panel p-6">
					<h3 class="font-display text-lg font-bold uppercase tracking-wide mb-4 pb-2 border-b border-[color:var(--border)]">Parameter Operasional &amp; Lingkungan</h3>
					<div class="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-5 gap-3">
						{#each operationalFields as f (f.k)}
							<div class="cell"><p class="cell-label">{f.l}</p><p class="cell-val text-base">{analysis.operational[f.k]}{f.u}</p></div>
						{/each}
						<div class="cell"><p class="cell-label">Oil Change Flag</p><p class="cell-val text-base">{analysis.operational.oil_change_flag ? 'YA' : 'TIDAK'}</p></div>
					</div>
				</div>

				<!-- RUL + SHAP -->
				<div class="grid grid-cols-1 md:grid-cols-2 gap-6">
					<div class="panel p-6">
						<h3 class="font-display text-lg font-bold uppercase tracking-wide mb-4 pb-2 border-b border-[color:var(--border)]">Prediksi Sisa Umur (RUL)</h3>
						<div class="py-2 space-y-3">
							<div class="rounded-xl border border-[color:var(--border)] bg-[color:var(--surface-2)] p-4">
								<p class="cell-label">Komponen Terlemah</p>
								<p class="font-display text-xl font-bold mt-0.5 leading-tight">{analysis.rul_prediction.component}</p>
							</div>
							<div class="grid grid-cols-2 lg:grid-cols-4 gap-3">
								<div class="col-span-2 rounded-xl bg-steel-gradient text-white p-4 flex flex-col justify-center">
									<p class="text-[10px] text-graphite-300 uppercase tracking-wider">Estimasi Sebelum Kegagalan</p>
									<p class="text-3xl md:text-4xl font-display font-bold text-amber mt-1 leading-none">{fmtHours(analysis.rul_prediction.hours_remaining)}</p>
									<p class="text-[10px] text-graphite-300 mt-1.5 font-mono">{Math.round(analysis.rul_prediction.hours_remaining)} jam total</p>
								</div>
								<div class="rounded-xl border border-[color:var(--border)] bg-[color:var(--surface-2)] p-4 flex flex-col justify-center">
									<p class="cell-label">Rentang Estimasi</p>
									<p class="font-display text-2xl font-bold mt-1 leading-none tabular-nums">{Math.round(analysis.rul_prediction.lower_bound)}<span class="text-[color:var(--text-faint)]">–</span>{Math.round(analysis.rul_prediction.upper_bound)}</p>
									<p class="text-[10px] text-[color:var(--text-muted)] mt-1 font-mono">jam (min–max)</p>
								</div>
								<div class="rounded-xl border border-[color:var(--border)] bg-[color:var(--surface-2)] p-4 flex flex-col justify-center">
									<p class="cell-label">Confidence</p>
									<p class="font-display text-2xl font-bold mt-1 leading-none" style="color:{analysis.rul_prediction.confidence >= 80 ? '#1FA971' : analysis.rul_prediction.confidence >= 60 ? '#E0A106' : '#E0413E'}">{analysis.rul_prediction.confidence}%</p>
									<div class="mt-2 h-1.5 rounded-full bg-[color:var(--border)] overflow-hidden">
										<div class="h-full rounded-full transition-all duration-700" style="width:{analysis.rul_prediction.confidence}%;background:{analysis.rul_prediction.confidence >= 80 ? '#1FA971' : analysis.rul_prediction.confidence >= 60 ? '#E0A106' : '#E0413E'}"></div>
									</div>
								</div>
							</div>
						</div>
					</div>
					<div class="panel p-6">
						<h3 class="font-display text-lg font-bold uppercase tracking-wide mb-2 pb-2 border-b border-[color:var(--border)]">Faktor Penyebab (SHAP)</h3>
						<p class="text-[10px] text-[color:var(--text-muted)] mb-2">Kontribusi tiap sensor terhadap skor risiko</p>
						<div style="height:224px;"><canvas id="shap"></canvas></div>
					</div>
				</div>
			</div>
		{/if}
	</div>
{/if}
