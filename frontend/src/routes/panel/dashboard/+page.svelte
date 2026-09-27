<script lang="ts">
	import { onMount, onDestroy, tick } from 'svelte';
	import { api } from '$lib/api';
	import { createMap } from '$lib/fleet-map';
	import { resolveModel } from '$lib/models';
	import ModeSelector from '$lib/components/ModeSelector.svelte';
	import ModeLockTabel from '$lib/components/ModeLockTabel.svelte';
	import { auth } from '$lib/stores/auth.svelte';
	import { theme } from '$lib/stores/theme.svelte';

	let isLoading = $state(true);
	let dashboardKPI = $state({ totalUnits: 0, activeUnits: 0, criticalUnits: 0, totalSavings: 0 });
	let statusDistribution = $state<{ label: string; jumlah: number; color: string }[]>([]);
	let monthlyFleetData = $state<any[]>([]);
	let mapLocations = $state<any[]>([]);
	let units = $state<any[]>([]);
	let featuredUnit = $state<any>(null);
	let unitPage = $state(1);
	const unitsPerPage = 6;

	let leafletMap: any = null;
	let chart: any = null;
	let mapFullscreen = $state(false);
	let fullMap: any = null;
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
	const totalFleetSavings = $derived(units.reduce((a, u) => a + (u.savings || 0), 0));

	function statusHex(s: string) {
		return { SEHAT: '#1FA971', WARNING: '#E0A106', CRITICAL: '#E0413E', RUSAK: '#7A848E' }[s] || '#7A848E';
	}

	function css(v: string) {
		if (typeof window === 'undefined') return '';
		return getComputedStyle(document.documentElement).getPropertyValue(v).trim();
	}
	function chartTheme() {
		return {
			tick: css('--text-muted') || '#5d6b7a',
			grid: css('--border') || '#d7dde4',
			axis: css('--border-cstrong') || css('--border-strong') || '#c2cad3',
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
					{ label: 'Sehat', data: monthlyFleetData.map((d) => d.sehat.val), borderColor: '#1FA971', backgroundColor: 'rgba(31,169,113,0.12)', borderWidth: 2.5, pointRadius: 3, tension: 0.35, fill: true },
					{ label: 'Warning', data: monthlyFleetData.map((d) => d.warning.val), borderColor: '#E0A106', backgroundColor: 'rgba(224,161,6,0.10)', borderWidth: 2.5, pointRadius: 3, tension: 0.35 },
					{ label: 'Critical', data: monthlyFleetData.map((d) => d.critical.val), borderColor: '#E0413E', backgroundColor: 'rgba(224,65,62,0.10)', borderWidth: 2.5, pointRadius: 3, tension: 0.35 }
				]
			},
			options: {
				responsive: true,
				maintainAspectRatio: false,
				interaction: { mode: 'index', intersect: false },
				plugins: {
					legend: { display: false },
					tooltip: { backgroundColor: t.text, padding: 12, cornerRadius: 10 }
				},
				scales: {
					x: { grid: { color: t.grid }, ticks: { color: t.tick }, border: { color: t.axis } },
					y: { min: 0, max: 100, grid: { color: t.grid }, ticks: { color: t.tick, stepSize: 20 }, border: { color: t.axis } }
				},
				onClick: (_e, els) => {
					if (els.length) monthDetail = monthlyFleetData[els[0].index];
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

	function logout() {
		auth.clear();
		window.location.href = '/account/login';
	}

	onMount(async () => {
		auth.init();
		injectModelViewer();
		try {
			await Promise.all([loadDashboard(), loadUnits()]);
		} catch (e) {
			console.error('Failed to load dashboard', e);
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

	function injectModelViewer() {
		if (document.querySelector('script[data-model-viewer]')) return;
		const s = document.createElement('script');
		s.type = 'module';
		s.dataset.modelViewer = 'true';
		s.src = 'https://ajax.googleapis.com/ajax/libs/model-viewer/3.3.0/model-viewer.min.js';
		document.head.appendChild(s);
	}
</script>

<svelte:head>
	<title>Dashboard — Pratyaksa</title>
</svelte:head>

<header class="flex justify-between items-start mb-8 gap-4 flex-wrap">
	<div>
		<h1 class="font-display text-4xl md:text-5xl font-bold uppercase tracking-wide leading-none">Dashboard</h1>
		<p class="mt-2 text-[color:var(--text-muted)]">Ringkasan data analitik armada secara menyeluruh.</p>
	</div>
	<ModeSelector />
</header>

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
				<p class="font-display text-4xl font-bold mt-1">${dashboardKPI.totalSavings.toLocaleString()}</p>
			</div>
		{/if}
	</div>

	<div class="grid grid-cols-1 lg:grid-cols-3 gap-6">
		<!-- Chart -->
		<div class="lg:col-span-2 panel p-6 flex flex-col">
			<div class="flex justify-between items-center mb-5 pb-4 border-b border-[color:var(--border)] gap-4">
				<h3 class="font-display text-xl font-bold uppercase tracking-wide">Distribusi Status Armada</h3>
				<div class="flex gap-3 text-xs font-semibold">
					<span class="flex items-center gap-1.5"><span class="w-3 h-3 rounded-full bg-healthy"></span> Sehat</span>
					<span class="flex items-center gap-1.5"><span class="w-3 h-3 rounded-full bg-warning"></span> Warning</span>
					<span class="flex items-center gap-1.5"><span class="w-3 h-3 rounded-full bg-critical"></span> Critical</span>
				</div>
			</div>
			<div class="flex-1 w-full" style="height:300px;">
				{#if isLoading}
					<div class="w-full h-full shimmer rounded-xl"></div>
				{:else}
					<canvas id="utilizationChart"></canvas>
				{/if}
			</div>
		</div>

		<!-- Donut distribution -->
		<div class="panel p-6">
			<h3 class="font-display text-xl font-bold uppercase tracking-wide mb-5 pb-4 border-b border-[color:var(--border)]">Kondisi Armada</h3>
			<div class="space-y-3">
				{#each statusDistribution as s (s.label)}
					<div class="flex items-center justify-between">
						<span class="flex items-center gap-2 text-sm font-semibold"><span class="w-3 h-3 rounded-full" style="background:{s.color}"></span>{s.label}</span>
						<span class="font-display text-2xl font-bold" style="color:{s.color}">{s.jumlah}</span>
					</div>
				{/each}
			</div>
			<div class="mt-6 pt-5 border-t border-[color:var(--border)]">
				<p class="text-[11px] font-semibold uppercase tracking-wider text-[color:var(--text-muted)]">Total Saving Armada</p>
				<p class="font-display text-3xl font-bold text-amber mt-1">${totalFleetSavings.toLocaleString()}</p>
			</div>
		</div>
	</div>

	<!-- Map -->
	<div class="panel p-6">
		<div class="flex justify-between items-center mb-5">
			<h3 class="font-display text-xl font-bold uppercase tracking-wide">Peta Sebaran Unit</h3>
			<button class="btn btn-ghost !py-2 !px-3 text-xs" onclick={openMapFullscreen}>Perbesar</button>
		</div>
		<div id="mining-map" class="rounded-xl overflow-hidden border border-[color:var(--border)]" style="height:420px;"></div>
	</div>

	<!-- 3D Fleet grid -->
	<div class="panel p-6">
		<div class="flex justify-between items-center mb-5 flex-wrap gap-3">
			<h3 class="font-display text-xl font-bold uppercase tracking-wide">Armada 3D</h3>
			<div class="flex items-center gap-2">
				<button class="mini-pg" disabled={unitPage <= 1} onclick={() => (unitPage = Math.max(1, unitPage - 1))}>‹</button>
				<span class="text-xs font-semibold text-[color:var(--text-muted)]">{unitPage} / {unitTotalPages}</span>
				<button class="mini-pg" disabled={unitPage >= unitTotalPages} onclick={() => (unitPage = Math.min(unitTotalPages, unitPage + 1))}>›</button>
			</div>
		</div>
		<div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
			{#each pagedUnits as u (u.id)}
				<button
					class="text-left rounded-xl border border-[color:var(--border)] overflow-hidden bg-[color:var(--surface-2)] hover:border-amber transition-colors"
					onclick={() => (featuredUnit = u)}
				>
					<div class="h-28 relative" style="background:linear-gradient(135deg,#2c3643,#141a21)">
						{#if featuredUnit?.id === u.id}
							<model-viewer
								src={resolveModel(u.model3d_url, u.jenis_alat_berat_nama)}
								camera-controls
								auto-rotate
								style="width:100%;height:100%;background:transparent;outline:none;"
								interaction-prompt="none"
							></model-viewer>
						{/if}
						<span class="absolute top-2 right-2 text-[10px] font-bold px-2 py-0.5 rounded-full text-white" style="background:{statusHex(u.status)}">{u.status}</span>
					</div>
					<div class="p-3">
						<p class="font-semibold text-sm">{u.code}</p>
						<p class="text-[11px] text-[color:var(--text-muted)] truncate">{u.jenis_alat_berat_nama || 'Heavy Equipment'}</p>
						<div class="mt-2 flex items-center gap-2">
							<div class="flex-1 h-1.5 rounded-full bg-[color:var(--surface-3)] overflow-hidden">
								<div class="h-full rounded-full" style="width:{u.health}%;background:{statusHex(u.status)}"></div>
							</div>
							<span class="text-[10px] font-mono text-[color:var(--text-muted)]">{u.health}%</span>
						</div>
					</div>
				</button>
			{/each}
		</div>
	</div>
</div>

{#if mapFullscreen}
	<div class="fixed inset-0 z-[100] bg-black/70 backdrop-blur-sm p-4 flex items-center justify-center" role="presentation">
		<div class="panel-raised w-full h-full p-4 relative">
			<div class="flex justify-between items-center mb-3">
				<h3 class="font-display text-xl font-bold uppercase">Peta Sebaran Unit</h3>
				<button class="btn btn-ghost !py-2 !px-3" onclick={closeMapFullscreen}>Tutup</button>
			</div>
			<div id="mining-map-full" class="rounded-xl overflow-hidden border border-[color:var(--border)]" style="height:calc(100% - 60px);"></div>
		</div>
	</div>
{/if}

{#if monthDetail}
	<div class="fixed inset-0 z-[100] flex items-center justify-center p-4" role="presentation">
		<div class="modal-backdrop" onclick={() => (monthDetail = null)} role="presentation"></div>
		<div class="modal-card w-full max-w-md p-6 anim-pop">
			<div class="flex justify-between items-center mb-4">
				<h3 class="font-display text-2xl font-bold uppercase">Bulan {monthDetail.month}</h3>
				<button class="text-[color:var(--text-muted)]" onclick={() => (monthDetail = null)}>✕</button>
			</div>
			{#each [{ k: 'sehat', label: 'Sehat', color: '#1FA971' }, { k: 'warning', label: 'Warning', color: '#E0A106' }, { k: 'critical', label: 'Critical', color: '#E0413E' }] as item (item.k)}
				<div class="mb-3">
					<div class="flex justify-between text-sm font-semibold">
						<span style="color:{item.color}">{item.label}</span>
						<span>{monthDetail[item.k].val}%</span>
					</div>
					<p class="text-[11px] text-[color:var(--text-muted)] mt-1">
						{monthDetail[item.k].units?.length ? monthDetail[item.k].units.join(', ') : 'Tidak ada unit'}
					</p>
				</div>
			{/each}
		</div>
	</div>
{/if}
