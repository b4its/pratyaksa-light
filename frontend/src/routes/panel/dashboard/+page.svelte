<script lang="ts">
	import { onMount, onDestroy, tick } from 'svelte';
	import { api } from '$lib/api';
	import { createMap } from '$lib/fleet-map';
	import { resolveModel } from '$lib/models';
	import { auth } from '$lib/stores/auth.svelte';
	import { theme } from '$lib/stores/theme.svelte';

	let isLoading = $state(true);
	let error = $state('');
	let dashboardKPI = $state({ totalUnits: 0, activeUnits: 0, criticalUnits: 0, totalSavings: 0 });
	let statusDistribution = $state<{ label: string; jumlah: number; color: string }[]>([]);
	let monthlyFleetData = $state<any[]>([]);
	let mapLocations = $state<any[]>([]);
	let units = $state<any[]>([]);
	let featuredUnit = $state<any>(null);
	let unitPage = $state(1);
	const unitsPerPage = 6;

	let leafletMap: any = null;
	let fullMap: any = null;
	let chart: any = null;
	let mapFullscreen = $state(false);
	let reportOpen = $state(false);
	let monthDetail = $state<any>(null);

	const statusHexMap: Record<string, string> = {
		Sehat: '#1FA971',
		Warning: '#E0A106',
		Critical: '#E0413E',
		Rusak: '#7A848E'
	};

	const unitTotalPages = $derived(Math.max(1, Math.ceil(units.length / unitsPerPage)));
	const pagedUnits = $derived(units.slice((unitPage - 1) * unitsPerPage, unitPage * unitsPerPage));

	// Ringkasan nyata untuk laporan (dihitung dari data armada, bukan angka statis).
	const avgHealth = $derived(
		units.length ? Math.round(units.reduce((s, u) => s + (u.health || 0), 0) / units.length) : 0
	);
	const fleetAvailability = $derived(
		dashboardKPI.totalUnits ? Math.round((dashboardKPI.activeUnits / dashboardKPI.totalUnits) * 1000) / 10 : 0
	);

	function statusHex(s: string) {
		return (
			{ SEHAT: '#1FA971', WARNING: '#E0A106', CRITICAL: '#E0413E', RUSAK: '#7A848E' }[s] ||
			'#7A848E'
		);
	}
	function recommend(label: string) {
		return label === 'Sehat'
			? 'Pertahankan jadwal maintenance rutin.'
			: label === 'Warning'
				? 'Lakukan pengecekan dalam 48 jam ke depan.'
				: label === 'Critical'
					? 'Segera jadwalkan overhaul, stop operasi.'
					: 'Tunggu suku cadang dari supplier utama.';
	}

	function css(v: string) {
		if (typeof window === 'undefined') return '';
		return getComputedStyle(document.documentElement).getPropertyValue(v).trim();
	}
	function chartTheme() {
		return {
			tick: css('--text-muted') || '#5d6b7a',
			grid: css('--border') || '#d7dde4',
			axis: css('--border-strong') || '#c2cad3',
			surface: css('--surface') || '#ffffff',
			text: css('--text') || '#1b2128'
		};
	}

	async function loadDashboard() {
		const res: any = await api.getDashboardStats();
		const data = res.data;
		dashboardKPI = {
			totalUnits: data.total_units,
			activeUnits: data.active_units,
			criticalUnits: data.critical_units,
			totalSavings: data.total_savings
		};
		statusDistribution = data.status_distribution.map((s: any) => ({
			label: s.label,
			jumlah: s.jumlah,
			color: statusHexMap[s.label] || '#7A848E'
		}));
		monthlyFleetData = data.monthly_fleet_data;
		mapLocations = data.map_locations;
	}

	async function loadUnits() {
		const res: any = await api.getUnitTambang({ per_page: 100 });
		units = res.data.data;
		if (units.length) featuredUnit = units[0];
	}

	async function buildChart() {
		if (!monthlyFleetData.length) return;
		const canvas = document.getElementById('utilizationChart') as HTMLCanvasElement;
		if (!canvas) return;
		const { default: Chart } = await import('chart.js/auto');
		if (chart) chart.destroy();
		const t = chartTheme();
		chart = new Chart(canvas, {
			type: 'line',
			data: {
				labels: monthlyFleetData.map((d) => d.month),
				datasets: [
					{ label: 'Sehat', data: monthlyFleetData.map((d) => d.sehat.val), borderColor: '#1FA971', backgroundColor: 'rgba(31,169,113,0.12)', borderWidth: 2.5, pointRadius: 3, pointHoverRadius: 6, pointBackgroundColor: '#1FA971', pointBorderColor: t.surface, pointBorderWidth: 2, tension: 0.35, fill: true },
					{ label: 'Warning', data: monthlyFleetData.map((d) => d.warning.val), borderColor: '#E0A106', backgroundColor: 'rgba(224,161,6,0.10)', borderWidth: 2.5, pointRadius: 3, pointHoverRadius: 6, pointBackgroundColor: '#E0A106', pointBorderColor: t.surface, pointBorderWidth: 2, tension: 0.35 },
					{ label: 'Critical', data: monthlyFleetData.map((d) => d.critical.val), borderColor: '#E0413E', backgroundColor: 'rgba(224,65,62,0.10)', borderWidth: 2.5, pointRadius: 3, pointHoverRadius: 6, pointBackgroundColor: '#E0413E', pointBorderColor: t.surface, pointBorderWidth: 2, tension: 0.35 }
				]
			},
			options: {
				responsive: true,
				maintainAspectRatio: false,
				layout: { padding: 10 },
				interaction: { mode: 'index', intersect: false },
				plugins: {
					legend: { display: false },
					tooltip: {
						backgroundColor: t.text,
						titleColor: '#fff',
						bodyColor: '#e6eaef',
						borderColor: t.axis,
						borderWidth: 1,
						padding: 12,
						cornerRadius: 10,
						titleFont: { family: 'Inter', size: 13, weight: 'bold' },
						bodyFont: { family: 'JetBrains Mono', size: 11 },
						boxPadding: 6,
						usePointStyle: true,
						callbacks: {
							title: (ctx: any) => `Bulan: ${ctx[0].label}`,
							label: (ctx: any) => {
								const m = monthlyFleetData[ctx.dataIndex];
								const map = [m?.sehat, m?.warning, m?.critical];
								const item = map[ctx.datasetIndex];
								const labels = ['Sehat', 'Warning', 'Critical'];
								const unitList = item?.units?.slice(0, 2).join(', ') || '-';
								const extra = item?.units?.length > 2 ? ` (+${item.units.length - 2} unit...)` : '';
								return `${labels[ctx.datasetIndex]}: ${ctx.raw}% | ${unitList}${extra}`;
							},
							afterBody: () => '\n(Klik titik untuk rincian data)'
						}
					}
				},
				scales: {
					x: { grid: { color: t.grid }, ticks: { font: { family: 'Inter', weight: 'bold' }, color: t.tick }, border: { color: t.axis } },
					y: { min: 0, max: 100, grid: { color: t.grid }, ticks: { font: { family: 'JetBrains Mono' }, color: t.tick, stepSize: 20 }, border: { color: t.axis } }
				},
				onClick: (_e: any, els: any[]) => {
					if (els.length) openMonthDetail(els[0].index);
				}
			}
		});
	}

	async function buildMap() {
		if (!mapLocations.length) return;
		await tick();
		leafletMap = await createMap('mining-map', mapLocations as any, { zoom: 13, dark: theme.isDark });
	}

	function applyMapTheme(dark: boolean) {
		document.querySelectorAll('#mining-map, #mining-map-full').forEach((el) => el.classList.toggle('map-dark', dark));
	}

	function openMonthDetail(i: number) {
		monthDetail = monthlyFleetData[i];
	}
	function closeMonthDetail() {
		monthDetail = null;
	}

	async function openMapFullscreen() {
		mapFullscreen = true;
		await tick();
		fullMap = await createMap('mining-map-full', mapLocations as any, { zoom: 13, dark: theme.isDark });
	}
	function closeMapFullscreen() {
		if (fullMap) {
			fullMap.remove();
			fullMap = null;
		}
		mapFullscreen = false;
	}

	onMount(async () => {
		auth.init();
		try {
			await Promise.all([loadDashboard(), loadUnits()]);
			error = '';
		} catch (e: any) {
			error = e?.message || 'Gagal memuat data dashboard.';
		}
		isLoading = false;
		await tick();
		await Promise.all([buildChart(), buildMap()]);
	});

	onDestroy(() => {
		if (leafletMap) leafletMap.remove();
		if (fullMap) fullMap.remove();
		if (chart) chart.destroy();
	});

	// Tutup dialog teratas dengan tombol Escape.
	function onKeydown(e: KeyboardEvent) {
		if (e.key !== 'Escape') return;
		if (mapFullscreen) closeMapFullscreen();
		else if (monthDetail) closeMonthDetail();
		else if (reportOpen) reportOpen = false;
	}

	// Recolor chart & map when the theme toggles.
	$effect(() => {
		const dark = theme.isDark;
		tick().then(() => {
			applyMapTheme(dark);
			if (!chart) return;
			const t = chartTheme();
			const o: any = chart.options;
			o.scales.x.grid.color = t.grid;
			o.scales.x.ticks.color = t.tick;
			o.scales.x.border.color = t.axis;
			o.scales.y.grid.color = t.grid;
			o.scales.y.ticks.color = t.tick;
			o.scales.y.border.color = t.axis;
			o.plugins.tooltip.backgroundColor = t.text;
			o.plugins.tooltip.borderColor = t.axis;
			chart.data.datasets.forEach((d: any) => (d.pointBorderColor = t.surface));
			chart.update();
		});
	});
</script>

<svelte:head><title>Dashboard — Pratyaksa</title></svelte:head>
<svelte:window onkeydown={onKeydown} />

<header class="flex justify-between items-start mb-8 gap-4 flex-wrap">
	<div>
		<h1 class="font-display text-4xl md:text-5xl font-bold uppercase tracking-wide leading-none">Dashboard</h1>
		<p class="mt-2 text-[color:var(--text-muted)]">Ringkasan data analitik armada secara menyeluruh.</p>
	</div>
	<div class="flex items-center gap-3 flex-wrap">
		<div class="flex items-center gap-3 panel-flat px-3 py-2">
			<div class="w-8 h-8 rounded-full bg-steel-gradient flex items-center justify-center text-white font-bold text-xs">{(auth.user?.name || 'A').charAt(0).toUpperCase()}</div>
			<span class="font-semibold text-sm">{auth.user?.name || 'Admin'}</span>
		</div>
	</div>
</header>

{#if error}<div class="mb-6 px-4 py-3 rounded-xl bg-critical/10 border border-critical/40 text-critical font-semibold flex items-center gap-2">⚠️ {error}</div>{/if}

<div class="space-y-7">
	<!-- KPI -->
	<div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-5">
		{#if isLoading}
			{#each Array(4) as _, i (i)}
				<div class="panel p-6"><div class="h-4 w-24 shimmer rounded mb-4"></div><div class="h-10 w-32 shimmer rounded"></div></div>
			{/each}
		{:else}
			<div class="kpi anim-pop d-1 p-6" style="--accent:#3E92CC">
				<p class="text-[11px] font-semibold uppercase tracking-wider text-[color:var(--text-muted)] mb-2">Total Unit</p>
				<p class="font-display text-5xl font-bold">{dashboardKPI.totalUnits}</p>
			</div>
			<div class="kpi anim-pop d-2 p-6" style="--accent:#1FA971">
				<p class="text-[11px] font-semibold uppercase tracking-wider text-[color:var(--text-muted)] mb-2">Unit Aktif (Sehat)</p>
				<p class="font-display text-5xl font-bold text-healthy">{dashboardKPI.activeUnits}</p>
			</div>
			<div class="kpi anim-pop d-3 p-6" class:anim-glow={dashboardKPI.criticalUnits > 0} style="--accent:#E0413E">
				<p class="text-[11px] font-semibold uppercase tracking-wider text-[color:var(--text-muted)] mb-2">Kritis / Rusak</p>
				<p class="font-display text-5xl font-bold text-critical">{dashboardKPI.criticalUnits}</p>
			</div>
			<div class="kpi anim-pop d-4 p-6 text-white" style="--accent:#F2A60C;background:linear-gradient(135deg,#2c3643,#141a21)">
				<p class="text-[11px] font-semibold uppercase tracking-wider text-amber mb-2">Total Saving</p>
				<p class="font-display text-4xl font-bold mt-1">{dashboardKPI.totalSavings < 0 ? '-' : ''}${Math.abs(dashboardKPI.totalSavings).toLocaleString()}</p>
			</div>
		{/if}
	</div>

	<div class="grid grid-cols-1 lg:grid-cols-3 gap-6">
		<!-- Chart -->
		<div class="lg:col-span-2 panel p-6 flex flex-col">
			{#if isLoading}
				<div class="flex justify-between items-center mb-6 pb-4 border-b border-[color:var(--border)]">
					<div class="h-7 w-64 shimmer rounded"></div>
					<div class="h-7 w-24 shimmer rounded"></div>
				</div>
				<div class="flex-1 w-full h-72 shimmer rounded-xl"></div>
			{:else}
				<div class="flex justify-between items-start md:items-center flex-col md:flex-row mb-5 pb-4 border-b border-[color:var(--border)] gap-4">
					<div>
						<h2 class="font-display text-2xl font-bold uppercase tracking-wide">Statistik Kondisi Unit</h2>
						<div class="flex gap-4 mt-2 flex-wrap">
							<div class="flex items-center gap-2 text-xs font-semibold"><span class="w-3 h-3 rounded-full bg-healthy"></span> Sehat</div>
							<div class="flex items-center gap-2 text-xs font-semibold"><span class="w-3 h-3 rounded-full bg-warning"></span> Warning</div>
							<div class="flex items-center gap-2 text-xs font-semibold"><span class="w-3 h-3 rounded-full bg-critical"></span> Critical</div>
						</div>
					</div>
					<div class="flex gap-2 items-center">
						<span class="text-[10px] font-medium text-[color:var(--text-faint)] hidden sm:inline">💡 Klik titik untuk detail</span>
						<button class="btn btn-ghost !py-2 text-sm">Tahun 2026</button>
					</div>
				</div>
				<div class="flex-1 w-full h-80 relative mt-2 cursor-pointer">
					<canvas id="utilizationChart"></canvas>
				</div>
			{/if}
		</div>

		<!-- Distribusi -->
		<div class="panel p-6 flex flex-col">
			{#if isLoading}
				<div class="h-7 w-40 shimmer rounded mb-6"></div>
				<div class="flex-1 flex flex-col justify-center gap-6">
					{#each Array(4) as _, i (i)}
						<div>
							<div class="flex justify-between mb-2"><div class="h-4 w-16 shimmer rounded"></div><div class="h-4 w-12 shimmer rounded"></div></div>
							<div class="w-full h-3 shimmer rounded-full"></div>
						</div>
					{/each}
				</div>
			{:else}
				<h2 class="font-display text-2xl font-bold uppercase tracking-wide mb-6 pb-4 border-b border-[color:var(--border)]">Distribusi Total</h2>
				<div class="flex-1 flex flex-col justify-center gap-5">
					{#each statusDistribution as item, index (item.label)}
						<div>
							<div class="flex justify-between font-semibold text-sm mb-2">
								<span>{item.label}</span>
								<span class="font-mono text-[color:var(--text-muted)]">{item.jumlah}/{dashboardKPI.totalUnits}</span>
							</div>
							<div class="w-full h-3 rounded-full bg-[color:var(--surface-3)] overflow-hidden">
								<div class="h-full rounded-full animate-progress-grow" style="width:{(item.jumlah / dashboardKPI.totalUnits) * 100}%;background-color:{item.color};animation-delay:{index * 0.1}s"></div>
							</div>
						</div>
					{/each}
				</div>
				<button class="btn btn-dark w-full mt-7 !py-3" onclick={() => (reportOpen = true)}>Lihat Detail Laporan</button>
			{/if}
		</div>
	</div>

	<!-- ============ VISUAL 3D ARMADA ============ -->
	<div class="panel p-6 relative z-0">
		<div class="flex justify-between items-center mb-6 pb-4 border-b border-[color:var(--border)] flex-wrap gap-3">
			<div>
				<h2 class="font-display text-2xl font-bold uppercase tracking-wide">Visual 3D Armada</h2>
				<p class="text-xs text-[color:var(--text-muted)] mt-1">Klik unit untuk menampilkan model 3D interaktif · drag untuk putar 360°</p>
			</div>
			<span class="badge bg-steel/15 border-steel/40 text-steel"><span class="w-1.5 h-1.5 rounded-full bg-steel anim-live"></span> {units.length} Unit 3D</span>
		</div>

		{#if isLoading}
			<div class="w-full shimmer rounded-xl" style="height:420px;"></div>
		{:else}
			<div class="grid grid-cols-1 lg:grid-cols-3 gap-6">
				<!-- Featured big viewer -->
				<div class="lg:col-span-2">
					{#if featuredUnit}
						<div class="rounded-xl border border-[color:var(--border)] bg-steel-gradient relative overflow-hidden" style="height:420px;">
							<model-viewer
								src={resolveModel(featuredUnit.model3d_url, featuredUnit.jenis_alat_berat_nama)}
								alt={'Model 3D ' + featuredUnit.code}
								camera-controls
								auto-rotate
								auto-rotate-delay="0"
								rotation-per-second="32deg"
								shadow-intensity="1.5"
								exposure="1.15"
								environment-image="neutral"
								interaction-prompt="none"
								style="width:100%;height:100%;outline:none;background-color:transparent;"
							></model-viewer>
							<div class="absolute top-3 left-3 flex flex-col gap-2 pointer-events-none">
								<div class="bg-steel/90 text-white text-[10px] font-semibold px-2.5 py-1 rounded-full flex items-center gap-1.5"><span class="w-1.5 h-1.5 rounded-full bg-white anim-live"></span> LIVE 3D</div>
								<div class="bg-graphite-900/80 text-amber text-sm font-mono font-bold px-3 py-1 rounded-lg">{featuredUnit.code}</div>
							</div>
							<div class="absolute top-3 right-3 badge text-white" style="background-color:{statusHex(featuredUnit.status)};border-color:{statusHex(featuredUnit.status)}">{featuredUnit.status}</div>
							<div class="absolute bottom-0 left-0 right-0 bg-graphite-900/85 backdrop-blur text-white p-4 flex justify-between items-end">
								<div>
									<p class="font-display font-bold text-lg uppercase leading-tight">{featuredUnit.jenis_alat_berat_nama}</p>
									<p class="text-xs text-graphite-300">{featuredUnit.maintenance}</p>
								</div>
								<div class="text-right">
									<p class="text-[10px] text-graphite-400 uppercase tracking-wider">Health</p>
									<p class="text-3xl font-display font-bold" style="color:{statusHex(featuredUnit.status)}">{featuredUnit.health}%</p>
								</div>
							</div>
						</div>
					{/if}
				</div>

				<!-- Unit selector grid -->
				<div class="flex flex-col">
					<div class="grid grid-cols-2 gap-3 flex-1">
						{#each pagedUnits as u, i (u.id)}
							<button
								class="anim-pop relative overflow-hidden rounded-xl border text-left transition-all group {featuredUnit && featuredUnit.id === u.id ? 'border-amber ring-2 ring-amber/30' : 'border-[color:var(--border)] hover:-translate-y-1'}"
								style="animation-delay:{i * 0.05}s"
								onclick={() => (featuredUnit = u)}
							>
								<div class="h-28 bg-steel-gradient relative overflow-hidden">
									<model-viewer
										src={resolveModel(u.model3d_url, u.jenis_alat_berat_nama)}
										alt={'Model 3D ' + u.code}
										auto-rotate
										auto-rotate-delay="0"
										rotation-per-second="40deg"
										disable-zoom
										interaction-prompt="none"
										shadow-intensity="1"
										exposure="1.1"
										environment-image="neutral"
										style="width:100%;height:100%;outline:none;pointer-events:none;background-color:transparent;"
									></model-viewer>
									<div class="absolute top-1.5 right-1.5 w-3 h-3 rounded-full border-2 border-white" style="background-color:{statusHex(u.status)}"></div>
								</div>
								<div class="p-2.5 bg-[color:var(--surface)] border-t border-[color:var(--border)]">
									<p class="font-mono font-semibold text-xs truncate">{u.code}</p>
									<div class="flex items-center justify-between mt-1">
										<span class="text-[10px] text-[color:var(--text-faint)]">HP {u.health}%</span>
										<span class="text-[8px] font-semibold px-1.5 py-0.5 rounded text-white" style="background-color:{statusHex(u.status)}">{u.status}</span>
									</div>
								</div>
							</button>
						{/each}
					</div>
					{#if unitTotalPages > 1}
						<div class="flex items-center justify-between mt-3 pt-3 border-t border-[color:var(--border)]">
							<span class="text-[11px] font-medium text-[color:var(--text-faint)]">Hal {unitPage} / {unitTotalPages} · {units.length} unit</span>
							<div class="flex gap-1.5">
								<button class="mini-pg" disabled={unitPage === 1} onclick={() => (unitPage = Math.max(1, unitPage - 1))}>‹</button>
								<button class="mini-pg" disabled={unitPage === unitTotalPages} onclick={() => (unitPage = Math.min(unitTotalPages, unitPage + 1))}>›</button>
							</div>
						</div>
					{/if}
				</div>
			</div>
		{/if}
	</div>

	<!-- PETA -->
	<div class="panel p-6 flex flex-col relative z-0">
		<div class="flex justify-between items-center mb-5 pb-4 border-b border-[color:var(--border)] flex-wrap gap-3">
			{#if isLoading}
				<div class="h-7 w-64 shimmer rounded"></div>
			{:else}
				<h2 class="font-display text-2xl font-bold uppercase tracking-wide">Peta Sebaran Unit</h2>
				<div class="flex items-center gap-3 flex-wrap">
					<div class="hidden sm:flex gap-4 text-xs font-semibold">
						<div class="flex items-center gap-1.5"><span class="w-2.5 h-2.5 rounded-full bg-critical"></span> Critical</div>
						<div class="flex items-center gap-1.5"><span class="w-2.5 h-2.5 rounded-full bg-warning"></span> High</div>
						<div class="flex items-center gap-1.5"><span class="w-2.5 h-2.5 rounded-full bg-healthy"></span> Normal</div>
					</div>
					<button class="btn btn-ghost !py-2 text-sm" onclick={openMapFullscreen}>
						<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2"><path d="M4 8V4h4M16 4h4v4M20 16v4h-4M8 20H4v-4" /></svg>
						Layar Penuh
					</button>
				</div>
			{/if}
		</div>

		{#if isLoading}
			<div class="w-full shimmer rounded-xl" style="height:500px;"></div>
		{:else}
			<div class="relative w-full rounded-xl border border-[color:var(--border)] overflow-hidden isolate z-0" style="height:500px;">
				<div id="mining-map" class="w-full h-full bg-[color:var(--surface-3)]"></div>
				<div class="map-depth pointer-events-none absolute inset-0 z-[400]"></div>
			</div>
		{/if}
	</div>
</div>

<!-- Report Modal -->
{#if reportOpen}
	<div class="fixed inset-0 z-[100] flex items-center justify-center p-4" role="presentation">
		<div class="modal-backdrop" onclick={() => (reportOpen = false)} role="presentation"></div>
		<div class="modal-card w-full max-w-3xl flex flex-col max-h-[90vh] anim-pop">
			<div class="flex justify-between items-center px-6 py-4 bg-steel-gradient text-white">
				<h3 class="font-display text-2xl font-bold uppercase tracking-wide text-amber">Detail Laporan Analitik</h3>
				<button class="w-9 h-9 rounded-lg bg-white/10 hover:bg-critical text-white flex items-center justify-center transition-colors" onclick={() => (reportOpen = false)}>✕</button>
			</div>
			<div class="p-6 overflow-y-auto bg-[color:var(--surface-2)]">
				<h4 class="font-display text-xl font-bold uppercase tracking-wide mb-4">Ringkasan Eksekutif</h4>
				<div class="grid grid-cols-2 gap-4 mb-7">
					<div class="panel p-4">
						<p class="label">Rata-rata Kesehatan Armada</p>
						<p class="font-display text-3xl font-bold mt-1">{avgHealth}<span class="text-lg font-normal text-[color:var(--text-muted)]">%</span> <span class="text-sm font-normal text-[color:var(--text-muted)]">dari {dashboardKPI.totalUnits} unit</span></p>
					</div>
					<div class="panel p-4">
						<p class="label">Ketersediaan Fisik (PA)</p>
						<p class="font-display text-3xl font-bold text-healthy mt-1">{fleetAvailability}<span class="text-lg font-normal text-[color:var(--text-muted)]">%</span> <span class="text-sm font-normal text-[color:var(--text-muted)]">{dashboardKPI.activeUnits}/{dashboardKPI.totalUnits} unit sehat</span></p>
					</div>
				</div>
				<h4 class="font-display text-lg font-bold uppercase tracking-wide mb-4">Breakdown Status Armada</h4>
				<div class="panel overflow-hidden">
					<div class="overflow-x-auto">
						<table class="table-industrial">
							<thead>
								<tr><th>Kategori Status</th><th>Persentase</th><th>Aksi Lanjutan Rekomendasi</th></tr>
							</thead>
							<tbody>
								{#each statusDistribution as item, index (index)}
									<tr>
										<td><span class="badge text-white" style="background-color:{item.color};border-color:{item.color}">{item.label}</span></td>
										<td class="font-mono font-bold text-lg">{item.jumlah}/{dashboardKPI.totalUnits}</td>
										<td class="text-sm text-[color:var(--text-muted)]">{recommend(item.label)}</td>
									</tr>
								{/each}
							</tbody>
						</table>
					</div>
				</div>
				<div class="mt-7 flex justify-end">
					<button class="btn btn-amber px-6" onclick={() => (reportOpen = false)}>Tutup / Unduh PDF</button>
				</div>
			</div>
		</div>
	</div>
{/if}

<!-- Month Detail Modal -->
{#if monthDetail}
	<div class="fixed inset-0 z-[100] flex items-center justify-center p-4" role="presentation">
		<div class="modal-backdrop" onclick={closeMonthDetail} role="presentation"></div>
		<div class="modal-card w-full max-w-4xl flex flex-col max-h-[90vh] anim-pop">
			<div class="flex justify-between items-center px-6 py-4 border-b border-[color:var(--border)] bg-[color:var(--surface-2)]">
				<h3 class="font-display text-2xl font-bold uppercase tracking-wide">Detail Unit Bulan {monthDetail.month}</h3>
				<button class="w-9 h-9 rounded-lg hover:bg-critical/15 hover:text-critical text-[color:var(--text-muted)] flex items-center justify-center transition-colors" onclick={closeMonthDetail}>✕</button>
			</div>
			<div class="p-6 overflow-y-auto flex flex-col gap-4">
				{#each [{ k: 'sehat', label: 'Sehat', color: '#1FA971' }, { k: 'warning', label: 'Warning', color: '#E0A106' }, { k: 'critical', label: 'Critical', color: '#E0413E' }] as item (item.k)}
					<div class="panel p-4 border-l-4" style="border-left-color:{item.color}">
						<div class="flex items-center justify-between mb-2">
							<span class="badge text-white" style="background:{item.color};border-color:{item.color}">{item.label} ({monthDetail[item.k].val}%)</span>
							<span class="text-xs font-semibold" style="color:{item.color}">{monthDetail[item.k].units.length} Armada</span>
						</div>
						<p class="text-[color:var(--text-muted)] leading-relaxed text-sm">{monthDetail[item.k].units.length > 0 ? monthDetail[item.k].units.join(', ') : 'Tidak ada unit dalam kategori ini.'}</p>
					</div>
				{/each}
			</div>
		</div>
	</div>
{/if}

<!-- Fullscreen Map Modal -->
{#if mapFullscreen}
	<div class="fixed inset-0 z-[120] flex flex-col p-4 md:p-6" role="presentation">
		<div class="modal-backdrop" onclick={closeMapFullscreen} role="presentation"></div>
		<div class="modal-card relative z-10 flex flex-col flex-1 w-full max-w-[1500px] mx-auto overflow-hidden">
			<div class="flex justify-between items-center px-6 py-4 border-b border-[color:var(--border)] bg-[color:var(--surface-2)]">
				<div>
					<h3 class="font-display text-2xl font-bold uppercase tracking-wide">Peta Sebaran Unit</h3>
					<p class="text-xs text-[color:var(--text-muted)]">{mapLocations.length} unit · koordinat real-time</p>
				</div>
				<button class="w-9 h-9 rounded-lg hover:bg-critical/15 hover:text-critical text-[color:var(--text-muted)] flex items-center justify-center transition-colors" onclick={closeMapFullscreen}>✕</button>
			</div>
			<div class="relative flex-1">
				<div id="mining-map-full" class="absolute inset-0 bg-[color:var(--surface-3)]"></div>
				<div class="map-depth pointer-events-none absolute inset-0 z-[400]"></div>
			</div>
		</div>
	</div>
{/if}
