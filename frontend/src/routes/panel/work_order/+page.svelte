<script lang="ts">
	import { onMount, onDestroy, tick } from 'svelte';
	import { api } from '$lib/api';
	import { resolveModel } from '$lib/models';

	let workOrders = $state<any[]>([]);
	let units = $state<any[]>([]);
	let overview = $state<any>(null);
	let loading = $state(true);
	let error = $state('');
	let toast = $state<{ ok: boolean; msg: string } | null>(null);

	let woPage = $state(1);
	const perPage = 20;
	let woTotal = $state(0);
	let woTotalPages = $state(1);
	let statusFilter = $state('');

	let createOpen = $state(false);
	let detailOpen = $state(false);
	let selectedUnit = $state<any>(null);
	let selectedUnitAnalysis = $state<any>(null);
	let selectedWO = $state<any>(null);
	let saving = $state(false);

	let woForm = $state({ asset_code: '', component: 'Komponen Utama', technician: '', notes: '', status_unit: 'CRITICAL', priority: 'HIGH' });

	let statusChart: any = null;
	let priorityChart: any = null;
	let dueChart: any = null;

	const statusColors: Record<string, string> = { SEHAT: '#1FA971', WARNING: '#E0A106', CRITICAL: '#E0413E', RUSAK: '#7A848E', NORMAL: '#1FA971' };
	function statusHex(s: string) {
		return statusColors[s] || '#7A848E';
	}

	const woPageNumbers = $derived.by(() => {
		const out: number[] = [];
		const start = Math.max(1, woPage - 2);
		const end = Math.min(woTotalPages, start + 4);
		for (let i = start; i <= end; i++) out.push(i);
		return out;
	});

	const criticalUnits = $derived(units.filter((u) => u.status === 'CRITICAL'));
	const warningUnits = $derived(units.filter((u) => u.status === 'WARNING'));
	const rusakUnits = $derived(units.filter((u) => u.status === 'RUSAK'));

	function notify(ok: boolean, msg: string) {
		toast = { ok, msg };
		setTimeout(() => (toast = null), 3500);
	}

	function css(v: string) {
		if (typeof window === 'undefined') return '';
		return getComputedStyle(document.documentElement).getPropertyValue(v).trim();
	}

	async function loadUnits() {
		const res: any = await api.getUnitTambang({ per_page: 100 });
		units = res.data.data;
	}

	async function loadWorkOrders() {
		const res: any = await api.getWorkOrders({ page: woPage, per_page: perPage, wo_status: statusFilter || undefined });
		workOrders = res.data.data;
		woTotal = res.data.total;
		woTotalPages = res.data.total_pages || 1;
	}

	async function loadOverview() {
		const res: any = await api.getAnalisaOverview();
		overview = res.data;
	}

	async function selectUnit(u: any) {
		selectedUnit = u;
		selectedUnitAnalysis = null;
		try {
			const res: any = await api.getUnitAnalysis(u.id);
			selectedUnitAnalysis = res.data;
		} catch {
			/* ignore */
		}
	}

	function openCreate(u: any) {
		selectedUnit = u;
		woForm = {
			asset_code: u.code,
			component: selectedUnitAnalysis?.rul_prediction?.component || 'Komponen Utama',
			technician: '',
			notes: '',
			status_unit: u.status === 'WARNING' ? 'WARNING' : u.status === 'RUSAK' ? 'RUSAK' : 'CRITICAL',
			priority: u.status === 'WARNING' ? 'MEDIUM' : 'HIGH'
		};
		createOpen = true;
	}

	async function createWO(e: Event) {
		e.preventDefault();
		saving = true;
		try {
			await api.createWorkOrder({
				asset_code: woForm.asset_code,
				component: woForm.component,
				status_unit: woForm.status_unit,
				priority: woForm.priority,
				technician: woForm.technician || null,
				notes: woForm.notes || null,
				rul_hours: selectedUnitAnalysis?.rul_prediction?.hours_remaining || 0
			});
			notify(true, 'Work Order berhasil dibuat');
			createOpen = false;
			await loadWorkOrders();
		} catch (e: any) {
			notify(false, e?.message || 'Gagal membuat WO');
		} finally {
			saving = false;
		}
	}

	async function openDetail(wo: any) {
		try {
			const res: any = await api.getWorkOrder(wo.id);
			selectedWO = res.data;
			detailOpen = true;
		} catch (e: any) {
			notify(false, e?.message || 'Gagal memuat detail');
		}
	}

	async function updateStatus(wo: any, status: string) {
		try {
			await api.updateWorkOrder(wo.id, { wo_status: status });
			notify(true, 'Status diperbarui');
			await loadWorkOrders();
		} catch (e: any) {
			notify(false, e?.message || 'Gagal update status');
		}
	}

	async function buildCharts() {
		const { default: Chart } = await import('chart.js/auto');
		const t = css('--text-muted') || '#5d6b7a';
		const grid = css('--border') || '#d7dde4';

		const sc = document.getElementById('woStatusChart') as HTMLCanvasElement;
		if (sc) {
			if (statusChart) statusChart.destroy();
			statusChart = new Chart(sc, {
				type: 'doughnut',
				data: {
					labels: ['Critical', 'Warning', 'Rusak'],
					datasets: [{ data: [criticalUnits.length, warningUnits.length, rusakUnits.length], backgroundColor: ['#E0413E', '#E0A106', '#7A848E'], borderWidth: 0 }]
				},
				options: { responsive: true, maintainAspectRatio: false, cutout: '62%', plugins: { legend: { position: 'bottom', labels: { color: t, boxWidth: 12 } } } }
			});
		}

		const pc = document.getElementById('woPriorityChart') as HTMLCanvasElement;
		if (pc) {
			if (priorityChart) priorityChart.destroy();
			const counts = { HIGH: 0, MEDIUM: 0, LOW: 0 } as Record<string, number>;
			workOrders.forEach((w) => (counts[w.priority] = (counts[w.priority] || 0) + 1));
			priorityChart = new Chart(pc, {
				type: 'bar',
				data: { labels: ['HIGH', 'MEDIUM', 'LOW'], datasets: [{ data: [counts.HIGH, counts.MEDIUM, counts.LOW], backgroundColor: ['#E0413E', '#E0A106', '#3E92CC'], borderRadius: 6 }] },
				options: { responsive: true, maintainAspectRatio: false, plugins: { legend: { display: false } }, scales: { x: { grid: { display: false }, ticks: { color: t } }, y: { grid: { color: grid }, ticks: { color: t } } } }
			});
		}

		const dc = document.getElementById('woDueChart') as HTMLCanvasElement;
		if (dc) {
			if (dueChart) dueChart.destroy();
			const days = Array.from({ length: 14 }, (_, i) => i + 1);
			const data = days.map(() => 0);
			workOrders.forEach((w) => {
				if (!w.est_completion_at) return;
				const diff = Math.ceil((new Date(w.est_completion_at).getTime() - Date.now()) / 86400000);
				if (diff >= 1 && diff <= 14) data[diff - 1]++;
			});
			dueChart = new Chart(dc, {
				type: 'line',
				data: { labels: days.map((d) => `H+${d}`), datasets: [{ data, borderColor: '#3E92CC', backgroundColor: 'rgba(62,146,204,0.15)', fill: true, tension: 0.35, pointRadius: 2 }] },
				options: { responsive: true, maintainAspectRatio: false, plugins: { legend: { display: false } }, scales: { x: { grid: { color: grid }, ticks: { color: t, maxTicksLimit: 7 } }, y: { grid: { color: grid }, ticks: { color: t, precision: 0 } } } }
			});
		}
	}

	onMount(async () => {
		try {
			await Promise.all([loadUnits(), loadWorkOrders(), loadOverview()]);
			await tick();
			await buildCharts();
			if (units.length) await selectUnit(units[0]);
		} catch (e: any) {
			error = e?.message || 'Gagal memuat data';
		} finally {
			loading = false;
		}
	});

	onDestroy(() => {
		[statusChart, priorityChart, dueChart].forEach((c) => c && c.destroy());
	});

	async function changePage(p: number) {
		woPage = p;
		await loadWorkOrders();
	}
</script>

<svelte:head><title>Work Order — Pratyaksa</title></svelte:head>

<header class="flex justify-between items-start mb-8 gap-4 flex-wrap">
	<div>
		<h1 class="font-display text-4xl md:text-5xl font-bold uppercase tracking-wide leading-none">Work Order</h1>
		<p class="mt-2 text-[color:var(--text-muted)]">Manajemen tiket pemeliharaan prediktif (CMMS).</p>
	</div>
	{#if units.length}
		<button class="btn btn-amber" onclick={() => openCreate(units.find((u) => u.status !== 'SEHAT') || units[0])}>+ Buat Work Order</button>
	{/if}
</header>

{#if toast}
	<div class="mb-4 px-4 py-2.5 rounded-lg text-sm font-semibold {toast.ok ? 'bg-healthy/10 text-healthy border border-healthy/30' : 'bg-critical/10 text-critical border border-critical/40'}">{toast.msg}</div>
{/if}
{#if error}<div class="mb-4 px-4 py-2.5 rounded-lg bg-critical/10 border border-critical/40 text-critical text-sm">{error}</div>{/if}

<div class="space-y-6">
	<!-- KPIs -->
	<div class="grid grid-cols-1 sm:grid-cols-3 gap-5">
		<div class="kpi p-6" style="--accent:#E0413E"><p class="text-[11px] font-semibold uppercase tracking-wider text-[color:var(--text-muted)]">Critical</p><p class="font-display text-4xl font-bold text-critical">{criticalUnits.length}</p></div>
		<div class="kpi p-6" style="--accent:#E0A106"><p class="text-[11px] font-semibold uppercase tracking-wider text-[color:var(--text-muted)]">Warning</p><p class="font-display text-4xl font-bold text-warning">{warningUnits.length}</p></div>
		<div class="kpi p-6" style="--accent:#7A848E"><p class="text-[11px] font-semibold uppercase tracking-wider text-[color:var(--text-muted)]">Rusak</p><p class="font-display text-4xl font-bold text-rusak">{rusakUnits.length}</p></div>
	</div>

	<!-- Charts -->
	<div class="grid grid-cols-1 lg:grid-cols-3 gap-6">
		<div class="panel p-6"><h3 class="font-display text-lg font-bold uppercase tracking-wide mb-3">Distribusi Status</h3><div style="height:220px;"><canvas id="woStatusChart"></canvas></div></div>
		<div class="panel p-6"><h3 class="font-display text-lg font-bold uppercase tracking-wide mb-3">Distribusi Prioritas</h3><div style="height:220px;"><canvas id="woPriorityChart"></canvas></div></div>
		<div class="panel p-6"><h3 class="font-display text-lg font-bold uppercase tracking-wide mb-3">Proyeksi Jatuh Tempo (14 hari)</h3><div style="height:220px;"><canvas id="woDueChart"></canvas></div></div>
	</div>

	<div class="grid grid-cols-1 lg:grid-cols-3 gap-6">
		<!-- Unit list -->
		<div class="panel p-6">
			<h3 class="font-display text-lg font-bold uppercase tracking-wide mb-3 pb-2 border-b border-[color:var(--border)]">Unit Prioritas</h3>
			<div class="space-y-2 max-h-96 overflow-y-auto">
				{#each units.filter((u) => u.status !== 'SEHAT') as u (u.id)}
					<button class="w-full text-left panel-flat p-3 hover:border-amber transition-colors" class:!border-amber={selectedUnit?.id === u.id} onclick={() => selectUnit(u)}>
						<div class="flex items-center justify-between">
							<span class="font-semibold text-sm">{u.code}</span>
							<span class="badge text-[10px]" style="color:{statusHex(u.status)};border-color:{statusHex(u.status)}55">{u.status}</span>
						</div>
						<p class="text-[11px] text-[color:var(--text-muted)] truncate">{u.jenis_alat_berat_nama}</p>
					</button>
				{:else}
					<p class="text-sm text-[color:var(--text-muted)]">Tidak ada unit berisiko.</p>
				{/each}
			</div>
		</div>

		<!-- Unit analysis -->
		<div class="lg:col-span-2 panel p-6">
			{#if selectedUnit}
				<div class="grid grid-cols-1 md:grid-cols-2 gap-6">
					<div>
						<h3 class="font-display text-xl font-bold uppercase">{selectedUnit.code}</h3>
						<p class="text-sm text-[color:var(--text-muted)] mb-3">{selectedUnit.jenis_alat_berat_nama}</p>
						<div class="h-44 rounded-xl overflow-hidden border border-[color:var(--border)]" style="background:linear-gradient(135deg,#2c3643,#141a21)">
							<model-viewer src={resolveModel(selectedUnit.model3d_url, selectedUnit.jenis_alat_berat_nama)} camera-controls auto-rotate style="width:100%;height:100%;background:transparent;" interaction-prompt="none"></model-viewer>
						</div>
						<button class="btn btn-amber w-full mt-4" onclick={() => openCreate(selectedUnit)}>Buat Work Order</button>
					</div>
					<div>
						{#if selectedUnitAnalysis}
							<div class="grid grid-cols-2 gap-3 mb-4">
								<div class="panel-flat p-3"><p class="text-[10px] uppercase text-[color:var(--text-faint)] font-semibold">Risk Score</p><p class="font-display text-3xl font-bold" style="color:{statusHex(selectedUnitAnalysis.risk_level)}">{selectedUnitAnalysis.risk_score}</p></div>
								<div class="panel-flat p-3"><p class="text-[10px] uppercase text-[color:var(--text-faint)] font-semibold">RUL ({selectedUnitAnalysis.rul_prediction.component})</p><p class="font-display text-2xl font-bold text-amber">{selectedUnitAnalysis.rul_prediction.hours_remaining} jam</p></div>
							</div>
							<h4 class="font-display text-sm font-bold uppercase mb-2">Kesehatan Komponen</h4>
							<div class="space-y-2">
								{#each selectedUnitAnalysis.component_health as c (c.component)}
									<div>
										<div class="flex justify-between text-[11px] font-semibold mb-0.5"><span>{c.component}</span><span>{c.health}%</span></div>
										<div class="h-1.5 rounded-full bg-[color:var(--surface-3)] overflow-hidden"><div class="h-full rounded-full" style="width:{c.health}%;background:{c.health < 45 ? '#E0413E' : c.health < 70 ? '#E0A106' : '#1FA971'}"></div></div>
									</div>
								{/each}
							</div>
						{:else}
							<p class="text-sm text-[color:var(--text-muted)]">Memuat analisa…</p>
						{/if}
					</div>
				</div>
			{:else}
				<p class="text-[color:var(--text-muted)]">Pilih unit untuk melihat analisa.</p>
			{/if}
		</div>
	</div>

	<!-- Saved WO table -->
	<div class="panel p-6">
		<div class="flex justify-between items-center mb-5 flex-wrap gap-3">
			<h3 class="font-display text-xl font-bold uppercase tracking-wide">Work Order Tersimpan</h3>
			<select bind:value={statusFilter} class="field" style="max-width:200px;" onchange={() => { woPage = 1; loadWorkOrders(); }}>
				<option value="">Semua Status</option>
				<option value="OPEN">OPEN</option>
				<option value="IN_PROGRESS">IN_PROGRESS</option>
				<option value="COMPLETED">COMPLETED</option>
				<option value="CANCELLED">CANCELLED</option>
			</select>
		</div>
		<div class="overflow-x-auto">
			<table class="table-industrial">
				<thead><tr><th>WO Number</th><th>Unit</th><th>Komponen</th><th>Prioritas</th><th>Teknisi</th><th>Status</th><th class="text-right">Aksi</th></tr></thead>
				<tbody>
					{#if loading}
						{#each Array(5) as _, i (i)}<tr><td colspan="7"><div class="h-4 shimmer rounded my-1"></div></td></tr>{/each}
					{:else if workOrders.length === 0}
						<tr><td colspan="7" class="text-center text-[color:var(--text-muted)] py-10">Belum ada work order.</td></tr>
					{:else}
						{#each workOrders as wo (wo.id)}
							<tr>
								<td class="font-mono font-semibold">{wo.wo_number}</td>
								<td>{wo.asset_code}</td>
								<td class="text-[color:var(--text-muted)]">{wo.component}</td>
								<td><span class="badge" style="color:{wo.priority === 'HIGH' ? '#E0413E' : wo.priority === 'MEDIUM' ? '#E0A106' : '#3E92CC'}">{wo.priority}</span></td>
								<td class="text-[color:var(--text-muted)]">{wo.technician || '-'}</td>
								<td><span class="badge" style="color:{wo.wo_status === 'COMPLETED' ? '#1FA971' : wo.wo_status === 'IN_PROGRESS' ? '#3E92CC' : wo.wo_status === 'CANCELLED' ? '#7A848E' : '#E0A106'}">{wo.wo_status}</span></td>
								<td class="text-right whitespace-nowrap">
									<button class="btn btn-ghost !py-1.5 !px-3 text-xs" onclick={() => openDetail(wo)}>Detail</button>
									{#if wo.wo_status !== 'COMPLETED' && wo.wo_status !== 'CANCELLED'}
										<button class="btn btn-amber !py-1.5 !px-3 text-xs ml-2" onclick={() => updateStatus(wo, 'COMPLETED')}>Selesai</button>
									{/if}
								</td>
							</tr>
						{/each}
					{/if}
				</tbody>
			</table>
		</div>
		<div class="flex items-center justify-between mt-5">
			<span class="text-xs text-[color:var(--text-muted)]">Total {woTotal} work order</span>
			<div class="flex items-center gap-1.5">
				<button class="mini-pg" disabled={woPage <= 1} onclick={() => changePage(woPage - 1)}>‹</button>
				{#each woPageNumbers as p (p)}<button class="mini-pg" class:!bg-amber={p === woPage} class:!text-graphite-900={p === woPage} onclick={() => changePage(p)}>{p}</button>{/each}
				<button class="mini-pg" disabled={woPage >= woTotalPages} onclick={() => changePage(woPage + 1)}>›</button>
			</div>
		</div>
	</div>
</div>

<!-- Create modal -->
{#if createOpen}
	<div class="fixed inset-0 z-[100] flex items-center justify-center p-4" role="presentation">
		<div class="modal-backdrop" onclick={() => (createOpen = false)} role="presentation"></div>
		<div class="modal-card w-full max-w-lg">
			<div class="h-1.5 hazard-stripe opacity-90"></div>
			<form onsubmit={createWO} class="p-6 space-y-4">
				<h3 class="font-display text-2xl font-bold uppercase">Buat Work Order</h3>
				<p class="text-sm text-[color:var(--text-muted)]">Unit: <span class="font-semibold text-[color:var(--text)]">{woForm.asset_code}</span></p>
				<div class="grid grid-cols-2 gap-4">
					<div>
						<label for="wostatus" class="label">Status Unit</label>
						<select id="wostatus" bind:value={woForm.status_unit} class="field"><option value="WARNING">WARNING</option><option value="CRITICAL">CRITICAL</option><option value="RUSAK">RUSAK</option></select>
					</div>
					<div>
						<label for="woprio" class="label">Prioritas</label>
						<select id="woprio" bind:value={woForm.priority} class="field"><option value="HIGH">HIGH</option><option value="MEDIUM">MEDIUM</option><option value="LOW">LOW</option></select>
					</div>
				</div>
				<div><label for="wocomp" class="label">Komponen Target</label><input id="wocomp" bind:value={woForm.component} class="field" /></div>
				<div><label for="wotech" class="label">Teknisi</label><input id="wotech" bind:value={woForm.technician} class="field" placeholder="Nama teknisi" /></div>
				<div><label for="wonotes" class="label">Catatan</label><textarea id="wonotes" bind:value={woForm.notes} class="field" rows="3"></textarea></div>
				<div class="flex justify-end gap-3">
					<button type="button" class="btn btn-ghost" onclick={() => (createOpen = false)}>Batal</button>
					<button type="submit" class="btn btn-amber" disabled={saving}>{saving ? 'Menyimpan…' : 'Buat WO'}</button>
				</div>
			</form>
		</div>
	</div>
{/if}

<!-- Detail modal -->
{#if detailOpen && selectedWO}
	<div class="fixed inset-0 z-[100] flex items-center justify-center p-4 overflow-y-auto" role="presentation">
		<div class="modal-backdrop" onclick={() => (detailOpen = false)} role="presentation"></div>
		<div class="modal-card w-full max-w-2xl my-8 p-6 anim-pop">
			<div class="flex justify-between items-center mb-4">
				<h3 class="font-display text-2xl font-bold uppercase">{selectedWO.work_order.wo_number}</h3>
				<button class="text-[color:var(--text-muted)]" onclick={() => (detailOpen = false)}>✕</button>
			</div>
			<div class="grid grid-cols-2 gap-3 text-sm">
				{#each Object.entries({ Unit: selectedWO.work_order.asset_code, Prioritas: selectedWO.work_order.priority, Komponen: selectedWO.work_order.component, 'Status Unit': selectedWO.work_order.status_unit, Teknisi: selectedWO.work_order.technician || '-', Status: selectedWO.work_order.wo_status, 'RUL (jam)': selectedWO.work_order.rul_hours, 'Estimasi Biaya': '$' + selectedWO.work_order.est_cost.toLocaleString() }) as [k, v] (k)}
					<div class="panel-flat p-3"><p class="text-[10px] uppercase text-[color:var(--text-faint)] font-semibold">{k}</p><p class="font-semibold">{v}</p></div>
				{/each}
			</div>
			{#if selectedWO.work_order.notes}
				<div class="mt-4 panel-flat p-3"><p class="text-[10px] uppercase text-[color:var(--text-faint)] font-semibold">Catatan</p><p class="text-sm">{selectedWO.work_order.notes}</p></div>
			{/if}
			{#if selectedWO.unit}
				<div class="mt-4">
					<h4 class="font-display text-sm font-bold uppercase mb-2">Unit Terkait</h4>
					<div class="grid grid-cols-2 gap-3 text-sm">
						<div class="panel-flat p-3"><p class="text-[10px] uppercase text-[color:var(--text-faint)] font-semibold">Kode Unit</p><p class="font-semibold">{selectedWO.unit.code}</p></div>
						<div class="panel-flat p-3"><p class="text-[10px] uppercase text-[color:var(--text-faint)] font-semibold">Health</p><p class="font-semibold">{selectedWO.unit.health}%</p></div>
					</div>
				</div>
			{/if}
			<div class="flex justify-end gap-3 mt-6">
				{#if selectedWO.work_order.wo_status !== 'COMPLETED'}
					<button class="btn btn-amber" onclick={() => { updateStatus(selectedWO.work_order, 'COMPLETED'); detailOpen = false; }}>Tandai Selesai</button>
				{/if}
				<button class="btn btn-ghost" onclick={() => (detailOpen = false)}>Tutup</button>
			</div>
		</div>
	</div>
{/if}
