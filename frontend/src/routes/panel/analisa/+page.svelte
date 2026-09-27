<script lang="ts">
	import { onMount, onDestroy, tick } from 'svelte';
	import { api } from '$lib/api';
	import { resolveModel } from '$lib/models';
	import { theme } from '$lib/stores/theme.svelte';

	let overview = $state<any>(null);
	let analysis = $state<any>(null);
	let selectedUnitId = $state<string>('');
	let loading = $state(true);
	let loadingUnit = $state(false);
	let error = $state('');

	let pieChart: any = null;
	let barChart: any = null;
	let gaugeChart: any = null;
	let trendChart: any = null;

	function css(v: string) {
		if (typeof window === 'undefined') return '';
		return getComputedStyle(document.documentElement).getPropertyValue(v).trim();
	}
	function themePalette() {
		return {
			tick: css('--text-muted') || '#5d6b7a',
			grid: css('--border') || '#d7dde4',
			text: css('--text') || '#1b2128',
			surface: css('--surface') || '#fff'
		};
	}

	const statusColors: Record<string, string> = {
		SEHAT: '#1FA971',
		WARNING: '#E0A106',
		CRITICAL: '#E0413E',
		RUSAK: '#7A848E',
		NORMAL: '#1FA971',
		LOW: '#1FA971',
		MEDIUM: '#E0A106',
		HIGH: '#E07A2C'
	};
	function riskColor(label: string) {
		return { LOW: '#1FA971', MEDIUM: '#E0A106', HIGH: '#E07A2C', CRITICAL: '#E0413E', NORMAL: '#1FA971', WARNING: '#E0A106' }[label] || '#7A848E';
	}
	function fmtHours(h: number) {
		if (h == null) return '-';
		if (h > 48) return `${Math.round(h / 24)} hari`;
		return `${Math.round(h)} jam`;
	}
	function rulTone(hours: number) {
		if (hours < 250) return '#E0413E';
		if (hours < 700) return '#E0A106';
		return '#1FA971';
	}

	async function loadOverview() {
		const res: any = await api.getAnalisaOverview();
		overview = res.data;
		if (overview.units?.length) {
			selectedUnitId = overview.units[0].id;
		}
	}

	async function loadUnit(id: string) {
		if (!id) return;
		loadingUnit = true;
		try {
			const res: any = await api.getUnitAnalysis(id);
			analysis = res.data;
			await tick();
			buildGauge();
			buildTrend();
		} catch (e: any) {
			error = e?.message || 'Gagal memuat analisa unit';
		} finally {
			loadingUnit = false;
		}
	}

	async function buildCharts() {
		const { default: Chart } = await import('chart.js/auto');
		const p = themePalette();

		const pie = document.getElementById('statusPie') as HTMLCanvasElement;
		if (pie && overview) {
			if (pieChart) pieChart.destroy();
			pieChart = new Chart(pie, {
				type: 'doughnut',
				data: {
					labels: overview.status_distribution.map((s: any) => s.label),
					datasets: [{ data: overview.status_distribution.map((s: any) => s.count), backgroundColor: overview.status_distribution.map((s: any) => statusColors[s.label] || '#7A848E'), borderWidth: 0 }]
				},
				options: { responsive: true, maintainAspectRatio: false, cutout: '62%', plugins: { legend: { position: 'bottom', labels: { color: p.tick, boxWidth: 12 } } } }
			});
		}

		const bar = document.getElementById('riskBar') as HTMLCanvasElement;
		if (bar && overview) {
			if (barChart) barChart.destroy();
			barChart = new Chart(bar, {
				type: 'bar',
				data: {
					labels: overview.risk_distribution.map((s: any) => s.label),
					datasets: [{ data: overview.risk_distribution.map((s: any) => s.count), backgroundColor: overview.risk_distribution.map((s: any) => riskColor(s.label)), borderRadius: 6 }]
				},
				options: { responsive: true, maintainAspectRatio: false, plugins: { legend: { display: false } }, scales: { x: { grid: { display: false }, ticks: { color: p.tick } }, y: { grid: { color: p.grid }, ticks: { color: p.tick } } } }
			});
		}
	}

	function buildGauge() {
		const el = document.getElementById('riskGauge') as HTMLCanvasElement;
		if (!el || !analysis) return;
		import('chart.js/auto').then(({ default: Chart }) => {
			if (gaugeChart) gaugeChart.destroy();
			const score = analysis.risk_score;
			const color = riskColor(analysis.risk_level);
			gaugeChart = new Chart(el, {
				type: 'doughnut',
				data: { labels: ['Risiko', 'Sisa'], datasets: [{ data: [score, 100 - score], backgroundColor: [color, 'rgba(122,132,142,0.15)'], borderWidth: 0 }] },
				options: { responsive: true, maintainAspectRatio: false, cutout: '72%', rotation: -120, circumference: 240, plugins: { legend: { display: false }, tooltip: { enabled: false } } }
			});
		});
	}

	function buildTrend() {
		const el = document.getElementById('sensorTrend') as HTMLCanvasElement;
		if (!el || !analysis) return;
		import('chart.js/auto').then(({ default: Chart }) => {
			if (trendChart) trendChart.destroy();
			const hist = analysis.sensor_history;
			const p = themePalette();
			trendChart = new Chart(el, {
				type: 'line',
				data: {
					labels: hist.map((h: any) => h.time),
					datasets: [
						{ label: 'Suhu Mesin', data: hist.map((h: any) => h.suhu_mesin), borderColor: '#E0413E', tension: 0.35, pointRadius: 0 },
						{ label: 'Vibrasi×10', data: hist.map((h: any) => h.vibration * 10), borderColor: '#3E92CC', tension: 0.35, pointRadius: 0 },
						{ label: 'Akustik', data: hist.map((h: any) => h.acoustic), borderColor: '#F2A60C', tension: 0.35, pointRadius: 0 }
					]
				},
				options: { responsive: true, maintainAspectRatio: false, plugins: { legend: { labels: { color: p.tick, boxWidth: 12 } } }, scales: { x: { grid: { color: p.grid }, ticks: { color: p.tick, maxTicksLimit: 8 } }, y: { grid: { color: p.grid }, ticks: { color: p.tick } } } }
			});
		});
	}

	onMount(async () => {
		try {
			await loadOverview();
			await buildCharts();
			if (selectedUnitId) await loadUnit(selectedUnitId);
		} catch (e: any) {
			error = e?.message || 'Gagal memuat data analisa';
		} finally {
			loading = false;
		}
	});

	onDestroy(() => {
		[pieChart, barChart, gaugeChart, trendChart].forEach((c) => c && c.destroy());
	});

	async function onUnitChange(e: Event) {
		selectedUnitId = (e.target as HTMLSelectElement).value;
		await loadUnit(selectedUnitId);
	}
</script>

<svelte:head><title>Analisa Kerusakan — Pratyaksa</title></svelte:head>

<header class="mb-8">
	<h1 class="font-display text-4xl md:text-5xl font-bold uppercase tracking-wide leading-none">Analisa Kerusakan</h1>
	<p class="mt-2 text-[color:var(--text-muted)]">Analitik kesehatan armada realtime, prediksi RUL & explainability AI.</p>
</header>

{#if error}<div class="mb-4 px-4 py-2.5 rounded-lg bg-critical/10 border border-critical/40 text-critical text-sm">{error}</div>{/if}

{#if loading}
	<div class="panel p-10 text-center text-[color:var(--text-muted)]">Memuat analitik…</div>
{:else if overview}
	<div class="space-y-6">
		<!-- Overview KPI -->
		<div class="grid grid-cols-2 lg:grid-cols-4 gap-5">
			<div class="kpi p-6" style="--accent:#3E92CC"><p class="text-[11px] font-semibold uppercase tracking-wider text-[color:var(--text-muted)] mb-1">Total Unit</p><p class="font-display text-4xl font-bold">{overview.total_units}</p></div>
			<div class="kpi p-6" style="--accent:#1FA971"><p class="text-[11px] font-semibold uppercase tracking-wider text-[color:var(--text-muted)] mb-1">Rata-rata Health</p><p class="font-display text-4xl font-bold text-healthy">{overview.avg_health}%</p></div>
			<div class="kpi p-6" style="--accent:#E0A106"><p class="text-[11px] font-semibold uppercase tracking-wider text-[color:var(--text-muted)] mb-1">Rata-rata Risk</p><p class="font-display text-4xl font-bold text-warning">{overview.avg_risk_score}</p></div>
			<div class="kpi p-6" style="--accent:#E0413E"><p class="text-[11px] font-semibold uppercase tracking-wider text-[color:var(--text-muted)] mb-1">Unit Berisiko</p><p class="font-display text-4xl font-bold text-critical">{overview.units_at_risk}</p></div>
		</div>

		<!-- Charts -->
		<div class="grid grid-cols-1 lg:grid-cols-2 gap-6">
			<div class="panel p-6"><h2 class="font-display text-xl font-bold uppercase tracking-wide mb-4 pb-2 border-b border-[color:var(--border)]">Distribusi Status Armada</h2><div style="height:256px;"><canvas id="statusPie"></canvas></div></div>
			<div class="panel p-6"><h2 class="font-display text-xl font-bold uppercase tracking-wide mb-4 pb-2 border-b border-[color:var(--border)]">Distribusi Tingkat Risiko</h2><div style="height:256px;"><canvas id="riskBar"></canvas></div></div>
		</div>

		<!-- Unit selector -->
		<div class="panel p-6">
			<h2 class="font-display text-lg font-bold uppercase tracking-wide mb-4 pb-2 border-b border-[color:var(--border)]">Pilih Unit</h2>
			<select class="field" style="max-width:360px;" value={selectedUnitId} onchange={onUnitChange}>
				{#each overview.units as u (u.id)}
					<option value={u.id}>{u.code} — {u.jenis_alat_berat_nama || 'Heavy Equipment'} ({u.status})</option>
				{/each}
			</select>
		</div>

		{#if loadingUnit}
			<div class="panel p-10 text-center text-[color:var(--text-muted)]">Memuat analisa unit…</div>
		{:else if analysis}
			<div class="grid grid-cols-1 lg:grid-cols-3 gap-6">
				<!-- 3D -->
				<div class="panel p-6">
					<h3 class="font-display text-lg font-bold uppercase tracking-wide mb-3 pb-2 border-b border-[color:var(--border)]">Visual 3D Unit</h3>
					<div class="h-56 rounded-xl overflow-hidden border border-[color:var(--border)]" style="background:linear-gradient(135deg,#2c3643,#141a21)">
						<model-viewer src={resolveModel(analysis.unit.model3d_url, analysis.unit.jenis_alat_berat_nama)} camera-controls auto-rotate style="width:100%;height:100%;background:transparent;" interaction-prompt="none"></model-viewer>
					</div>
					<p class="font-display font-bold text-xl uppercase tracking-wide mt-4">{analysis.unit.code}</p>
					<p class="text-sm text-[color:var(--text-muted)]">{analysis.unit.jenis_alat_berat_nama}</p>
					<div class="flex items-center justify-between mt-3">
						<span class="badge" style="color:{statusColors[analysis.unit.status]};border-color:{statusColors[analysis.unit.status]}55">{analysis.unit.status}</span>
						<span class="font-display font-bold">{analysis.unit.health}%</span>
					</div>
				</div>

				<!-- Risk gauge -->
				<div class="panel p-6">
					<h3 class="font-display text-lg font-bold uppercase tracking-wide mb-3 pb-2 border-b border-[color:var(--border)]">Risk Score</h3>
					<div style="height:200px;" class="relative">
						<canvas id="riskGauge"></canvas>
						<div class="absolute inset-0 flex flex-col items-center justify-center pointer-events-none">
							<span class="font-display text-4xl font-bold" style="color:{riskColor(analysis.risk_level)}">{analysis.risk_score}</span>
							<span class="text-xs font-semibold uppercase tracking-wide" style="color:{riskColor(analysis.risk_level)}">{analysis.risk_level}</span>
						</div>
					</div>
				</div>

				<!-- Component health -->
				<div class="panel p-6">
					<h3 class="font-display text-lg font-bold uppercase tracking-wide mb-3 pb-2 border-b border-[color:var(--border)]">Kesehatan Komponen</h3>
					<div class="space-y-2.5">
						{#each analysis.component_health as c (c.component)}
							<div>
								<div class="flex justify-between text-xs font-semibold mb-1"><span>{c.component}</span><span>{c.health}%</span></div>
								<div class="h-2 rounded-full bg-[color:var(--surface-3)] overflow-hidden">
									<div class="h-full rounded-full" style="width:{c.health}%;background:{rulTone(c.health * 11)}"></div>
								</div>
							</div>
						{/each}
					</div>
				</div>
			</div>

			<div class="grid grid-cols-1 lg:grid-cols-2 gap-6">
				<!-- Sensor realtime -->
				<div class="panel p-6">
					<h3 class="font-display text-lg font-bold uppercase tracking-wide mb-4 pb-2 border-b border-[color:var(--border)]">Telemetri Sensor Real-Time</h3>
					<div class="grid grid-cols-2 gap-4">
						{#each Object.entries(analysis.sensor_readings) as [k, v] (k)}
							<div class="panel-flat p-3">
								<p class="text-[10px] font-semibold uppercase tracking-wider text-[color:var(--text-faint)]">{k.replace(/_/g, ' ')}</p>
								<p class="font-display text-2xl font-bold">{v}</p>
							</div>
						{/each}
					</div>
				</div>

				<!-- Trend -->
				<div class="panel p-6">
					<h3 class="font-display text-lg font-bold uppercase tracking-wide mb-4 pb-2 border-b border-[color:var(--border)]">Tren Sensor 24 Jam</h3>
					<div style="height:260px;"><canvas id="sensorTrend"></canvas></div>
				</div>
			</div>

			<!-- AI prediction -->
			<div class="grid grid-cols-1 lg:grid-cols-2 gap-6">
				<div class="panel p-6">
					<h3 class="font-display text-lg font-bold uppercase tracking-wide mb-4 pb-2 border-b border-[color:var(--border)]">Prediksi AI — Anomali & RUL</h3>
					<div class="grid grid-cols-3 gap-3 text-center">
						<div class="panel-flat p-3"><p class="text-[10px] uppercase text-[color:var(--text-faint)] font-semibold">XGBoost</p><p class="font-display text-2xl font-bold" style="color:{riskColor(analysis.prediction.xgb_anomaly_label)}">{analysis.prediction.xgb_anomaly_label}</p></div>
						<div class="panel-flat p-3"><p class="text-[10px] uppercase text-[color:var(--text-faint)] font-semibold">LSTM RUL</p><p class="font-display text-2xl font-bold">{analysis.prediction.lstm_rul_hours}</p></div>
						<div class="panel-flat p-3"><p class="text-[10px] uppercase text-[color:var(--text-faint)] font-semibold">Risk</p><p class="font-display text-2xl font-bold" style="color:{riskColor(analysis.prediction.risk_level)}">{analysis.prediction.risk_level}</p></div>
					</div>
					<p class="text-xs text-[color:var(--text-muted)] mt-4">Feature Drift: {analysis.prediction.drift_status.drift_detected ? 'Terdeteksi (' + analysis.prediction.drift_status.n_drifted + ')' : 'Tidak ada'}</p>
				</div>

				<!-- RUL prediction -->
				<div class="panel p-6">
					<h3 class="font-display text-lg font-bold uppercase tracking-wide mb-4 pb-2 border-b border-[color:var(--border)]">Prediksi Sisa Umur (RUL)</h3>
					<div class="grid grid-cols-2 gap-4">
						<div class="panel-flat p-4">
							<p class="text-[10px] uppercase text-[color:var(--text-faint)] font-semibold">Komponen Terlemah</p>
							<p class="font-display text-xl font-bold mt-1">{analysis.rul_prediction.component}</p>
							<p class="text-xs text-[color:var(--text-muted)] mt-2">Estimasi sebelum kegagalan</p>
							<p class="font-display text-3xl font-bold text-amber">{fmtHours(analysis.rul_prediction.hours_remaining)}</p>
						</div>
						<div class="panel-flat p-4 space-y-3">
							<div><p class="text-[10px] uppercase text-[color:var(--text-faint)] font-semibold">Rentang Estimasi</p><p class="font-semibold">{fmtHours(analysis.rul_prediction.lower_bound)} – {fmtHours(analysis.rul_prediction.upper_bound)}</p></div>
							<div><p class="text-[10px] uppercase text-[color:var(--text-faint)] font-semibold">Confidence</p><p class="font-display text-2xl font-bold text-healthy">{analysis.rul_prediction.confidence}%</p></div>
						</div>
					</div>
				</div>
			</div>

			<!-- Operational + SHAP -->
			<div class="grid grid-cols-1 lg:grid-cols-2 gap-6">
				<div class="panel p-6">
					<h3 class="font-display text-lg font-bold uppercase tracking-wide mb-4 pb-2 border-b border-[color:var(--border)]">Parameter Operasional & Lingkungan</h3>
					<div class="grid grid-cols-2 sm:grid-cols-3 gap-3">
						{#each Object.entries(analysis.operational) as [k, v] (k)}
							<div class="panel-flat p-2.5">
								<p class="text-[9px] font-semibold uppercase tracking-wider text-[color:var(--text-faint)] truncate">{k.replace(/_/g, ' ')}</p>
								<p class="font-semibold text-sm">{typeof v === 'boolean' ? (v ? 'Ya' : 'Tidak') : v}</p>
							</div>
						{/each}
					</div>
				</div>

				<div class="panel p-6">
					<h3 class="font-display text-lg font-bold uppercase tracking-wide mb-2 pb-2 border-b border-[color:var(--border)]">Faktor Penyebab (SHAP)</h3>
					<div class="space-y-2 mt-3">
						{#each analysis.shap_contributions as s (s.feature)}
							<div class="flex items-center gap-3">
								<span class="text-xs font-semibold w-40 truncate">{s.feature}</span>
								<div class="flex-1 h-2 rounded-full bg-[color:var(--surface-3)] overflow-hidden relative">
									<div class="h-full rounded-full" style="width:{Math.min(Math.abs(s.value) * 2, 100)}%;background:{s.value >= 0 ? '#E0413E' : '#1FA971'}"></div>
								</div>
								<span class="text-xs font-mono w-12 text-right">{s.value}</span>
							</div>
						{/each}
					</div>
				</div>
			</div>
		{/if}
	</div>
{/if}
