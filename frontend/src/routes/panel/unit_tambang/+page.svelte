<script lang="ts">
	import { onMount, onDestroy, tick } from 'svelte';
	import { api } from '$lib/api';
	import { createMap } from '$lib/fleet-map';
	import { resolveModel, modelForType } from '$lib/models';
	import ModeSelector from '$lib/components/ModeSelector.svelte';
	import ModeLockTabel from '$lib/components/ModeLockTabel.svelte';
	import { auth } from '$lib/stores/auth.svelte';
	import { theme } from '$lib/stores/theme.svelte';
	import { pratyaksa } from '$lib/stores/pratyaksa.svelte';

	const perPage = 5;

	let units = $state<any[]>([]);
	let total = $state(0);
	let currentPage = $state(1);
	let searchQuery = $state('');
	let filterStatus = $state('');
	let isLoading = $state(false);
	let error = $state('');
	let jenisOptions = $state<{ id: string; nama: string }[]>([]);
	const statusOptions = ['SEHAT', 'WARNING', 'CRITICAL', 'RUSAK'];

	const totalPages = $derived(Math.max(1, Math.ceil(total / perPage)));
	const visiblePages = $derived.by(() => {
		const max = 3;
		const tp = totalPages;
		const cp = currentPage;
		if (tp <= max) return Array.from({ length: tp }, (_, i) => i + 1);
		let start = Math.max(1, cp - 1);
		const end = Math.min(tp, start + max - 1);
		if (end === tp) start = Math.max(1, tp - max + 1);
		return Array.from({ length: end - start + 1 }, (_, i) => start + i);
	});

	// Modals
	let isDetailOpen = $state(false);
	let selectedUnit = $state<any>(null);
	let isFormOpen = $state(false);
	let formMode = $state<'add' | 'edit'>('add');
	let formData = $state<any>({});
	let formError = $state('');
	let formLoading = $state(false);
	let isExportOpen = $state(false);

	// Model 3D: link vs upload
	let model3dMode = $state<'link' | 'upload'>('link');
	let modelUploading = $state(false);
	let modelFileName = $state('');

	// Sensor map
	let sensorMap: any = null;
	let sensorFullMap: any = null;
	let isMapFullscreen = $state(false);
	let mapUnitCount = $state(0);

	const statusHex = (s: string) =>
		({ SEHAT: '#1FA971', WARNING: '#E0A106', CRITICAL: '#E0413E', RUSAK: '#7A848E' })[s] ||
		'#7A848E';
	const levelFor = (s: string) =>
		({ SEHAT: 'L', WARNING: 'H', CRITICAL: 'I', RUSAK: 'X' })[s] || 'L';

	async function fetchUnits() {
		isLoading = true;
		error = '';
		try {
			const res: any = await api.getUnitTambang({
				page: currentPage,
				per_page: perPage,
				search: searchQuery || undefined,
				status: filterStatus || undefined
			});
			units = res.data.data;
			total = res.data.total;
		} catch (e: any) {
			error = e?.message || 'Gagal memuat data unit.';
		} finally {
			isLoading = false;
		}
	}

	async function fetchJenisOptions() {
		try {
			const res: any = await api.getJenisAlatBerat({ per_page: 100 });
			jenisOptions = res.data.data.map((j: any) => ({ id: j.id, nama: j.nama }));
		} catch {
			/* ignore */
		}
	}

	function onSearch() {
		currentPage = 1;
		fetchUnits();
	}
	function gotoPage(p: number) {
		currentPage = p;
		fetchUnits();
	}

	// --- map ---
	async function buildLocations() {
		const res: any = await api.getUnitTambang({ per_page: 100 });
		return (res.data.data as any[])
			.filter((u) => u.lat != null && u.lng != null)
			.map((u) => ({
				unit: u.code,
				unit_type: u.jenis_alat_berat_nama || 'Heavy Equipment',
				status: u.status,
				color_hex: statusHex(u.status),
				level: levelFor(u.status),
				lat: u.lat,
				lng: u.lng,
				health: u.health
			}));
	}

	async function loadSensorMap() {
		try {
			const locs = await buildLocations();
			mapUnitCount = locs.length;
			await tick();
			if (sensorMap) {
				sensorMap.remove();
				sensorMap = null;
			}
			sensorMap = await createMap('sensor-map', locs as any, { dark: theme.isDark });
		} catch {
			/* ignore */
		}
	}

	async function openMapFullscreen() {
		isMapFullscreen = true;
		const locs = await buildLocations();
		await tick();
		sensorFullMap = await createMap('sensor-map-full', locs as any, { dark: theme.isDark });
	}
	function closeMapFullscreen() {
		if (sensorFullMap) {
			sensorFullMap.remove();
			sensorFullMap = null;
		}
		isMapFullscreen = false;
	}

	// --- CRUD ---
	function openDetail(unit: any) {
		selectedUnit = unit;
		isDetailOpen = true;
	}

	function openAdd() {
		formMode = 'add';
		formData = {
			code: '',
			jenis_alat_berat_id: jenisOptions[0]?.id || '',
			status: 'SEHAT',
			health: 100,
			maintenance: '30 Hari Lagi',
			savings: 0,
			lat: -0.5032,
			lng: 117.1536,
			img_url: 'https://placehold.co/400x250?text=Unit+Baru',
			model3d_url: modelForType(jenisOptions[0]?.nama)
		};
		model3dMode = 'link';
		modelFileName = '';
		formError = '';
		isFormOpen = true;
	}

	function openEdit(unit: any) {
		formMode = 'edit';
		formData = {
			id: unit.id,
			code: unit.code,
			jenis_alat_berat_id: unit.jenis_alat_berat_id,
			status: unit.status,
			health: unit.health,
			maintenance: unit.maintenance,
			savings: unit.savings,
			lat: unit.lat,
			lng: unit.lng,
			img_url: unit.img_url || '',
			model3d_url: unit.model3d_url || ''
		};
		const isUploaded = (unit.model3d_url || '').startsWith('/media/');
		model3dMode = isUploaded ? 'upload' : 'link';
		modelFileName = isUploaded ? (unit.model3d_url || '').split('/').pop() || '' : '';
		formError = '';
		isFormOpen = true;
	}

	async function save() {
		if (!formData.code?.trim()) {
			formError = 'Kode unit wajib diisi.';
			return;
		}
		if (formData.code.trim().length < 2) {
			formError = 'Kode unit minimal 2 karakter.';
			return;
		}
		if (!formData.jenis_alat_berat_id) {
			formError = 'Jenis alat berat wajib dipilih.';
			return;
		}
		if (!formData.maintenance?.trim()) {
			formError = 'Jadwal maintenance wajib diisi.';
			return;
		}
		formLoading = true;
		formError = '';
		try {
			const payload = {
				code: formData.code,
				jenis_alat_berat_id: formData.jenis_alat_berat_id,
				status: formData.status,
				health: Number(formData.health),
				maintenance: formData.maintenance,
				savings: Number(formData.savings),
				img_url: formData.img_url || undefined,
				model3d_url: formData.model3d_url || undefined,
				lat:
					formData.lat !== '' && formData.lat != null ? Number(formData.lat) : undefined,
				lng:
					formData.lng !== '' && formData.lng != null ? Number(formData.lng) : undefined
			};
			if (formMode === 'add') {
				await api.createUnitTambang(payload);
			} else {
				await api.updateUnitTambang(formData.id, payload);
			}
			isFormOpen = false;
			await fetchUnits();
			await loadSensorMap();
		} catch (e: any) {
			formError = e?.message || 'Gagal menyimpan.';
		} finally {
			formLoading = false;
		}
	}

	async function remove(unit: any) {
		if (!confirm(`Hapus unit "${unit.code}"?`)) return;
		try {
			await api.deleteUnitTambang(unit.id);
			await fetchUnits();
			await loadSensorMap();
		} catch (e: any) {
			alert(e?.message || 'Gagal menghapus.');
		}
	}

	async function onModelFileChange(e: Event) {
		const input = e.target as HTMLInputElement;
		const file = input.files?.[0];
		if (!file) return;
		const name = file.name.toLowerCase();
		if (!name.endsWith('.glb') && !name.endsWith('.gltf')) {
			formError = 'Format model harus .glb atau .gltf.';
			return;
		}
		modelUploading = true;
		formError = '';
		try {
			const res: any = await api.uploadModel(file);
			formData.model3d_url = res.url;
			modelFileName = res.filename || file.name;
		} catch (err: any) {
			formError = err?.message || 'Gagal mengunggah model.';
		} finally {
			modelUploading = false;
		}
	}

	function exportCSV() {
		const headers = ['Kode', 'Jenis', 'Status', 'Health', 'Maintenance', 'Savings'];
		const rows = units.map((u) => [
			u.code,
			u.jenis_alat_berat_nama || '',
			u.status,
			u.health,
			u.maintenance,
			u.savings
		]);
		const csv = [headers, ...rows].map((r) => r.join(',')).join('\n');
		const blob = new Blob([csv], { type: 'text/csv' });
		const url = URL.createObjectURL(blob);
		const a = document.createElement('a');
		a.href = url;
		a.download = 'unit_tambang.csv';
		a.click();
		URL.revokeObjectURL(url);
		isExportOpen = false;
	}

	onMount(async () => {
		await fetchJenisOptions();
		await fetchUnits();
		await loadSensorMap();
		pratyaksa.fetchAll();
		pratyaksa.startPolling(10000);
	});

	onDestroy(() => {
		if (sensorMap) sensorMap.remove();
		if (sensorFullMap) sensorFullMap.remove();
		pratyaksa.stopPolling();
	});

	$effect(() => {
		const dark = theme.isDark;
		tick().then(() => {
			document.querySelectorAll('#sensor-map, #sensor-map-full').forEach((el) => el.classList.toggle('map-dark', dark));
		});
	});
</script>

<svelte:head><title>Unit Tambang — Pratyaksa</title></svelte:head>

<header class="flex justify-between items-start mb-8 gap-4 flex-wrap">
	<div>
		<h1 class="font-display text-4xl md:text-5xl font-bold uppercase tracking-wide leading-none">Unit Tambang</h1>
		<p class="mt-2 text-[color:var(--text-muted)]">Unit yang beroperasi saat ini dan masih aktif berjalan.</p>
	</div>
	<div class="flex items-center gap-3 flex-wrap">
		<div class="flex items-center gap-3 panel-flat px-3 py-2">
			<div class="w-8 h-8 rounded-full bg-steel-gradient flex items-center justify-center text-white font-bold text-xs">{(auth.user?.name || 'A').charAt(0).toUpperCase()}</div>
			<span class="font-semibold text-sm">{auth.user?.name || 'Admin'}</span>
		</div>
		<ModeSelector />
	</div>
</header>

<ModeLockTabel />

{#if error}
	<div class="mb-6 px-4 py-3 rounded-xl bg-critical/10 border border-critical/40 text-critical font-semibold flex items-center gap-2">⚠️ {error}</div>
{/if}

<!-- Actions Bar -->
<div class="flex justify-between items-center mb-6 gap-3 flex-wrap">
	<div class="flex gap-3 flex-1 flex-wrap">
		<div class="relative flex-1" style="min-width:12rem;">
			<svg class="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-[color:var(--text-faint)]" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2"><circle cx="11" cy="11" r="8" /><path d="m21 21-4.3-4.3" /></svg>
			<input bind:value={searchQuery} onkeyup={(e) => e.key === 'Enter' && onSearch()} type="text" placeholder="Cari kode / nama unit..." class="field !pl-9" />
		</div>
		<select bind:value={filterStatus} onchange={onSearch} class="field cursor-pointer" style="width:auto;">
			<option value="">Semua Status</option>
			{#each statusOptions as s (s)}<option value={s}>{s}</option>{/each}
		</select>
		<button class="btn btn-ghost px-6" onclick={onSearch}>Cari</button>
		<button class="btn btn-dark px-5" onclick={() => (isExportOpen = true)}>
			Ekspor
			<svg class="w-4 h-4 text-amber" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2.5"><path d="M12 3v12m0 0l-4-4m4 4l4-4M4 21h16" /></svg>
		</button>
	</div>
	<button class="btn btn-amber px-5" onclick={openAdd}>
		<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2.5"><path d="M12 5v14M5 12h14" /></svg>
		Tambah Unit
	</button>
</div>

<!-- Table -->
<section class="panel-raised overflow-hidden">
	<div class="overflow-x-auto">
		<table class="table-industrial">
			<thead>
				<tr><th>Kode Unik</th><th>Nama Unit</th><th>Status</th><th>Health</th><th>Jadwal</th><th>Saving</th><th>Aksi</th></tr>
			</thead>
			<tbody>
				{#if isLoading}
					{#each Array(5) as _, i (i)}
						<tr>{#each Array(7) as __, j (j)}<td><div class="h-4 shimmer rounded"></div></td>{/each}</tr>
					{/each}
				{:else if units.length === 0}
					<tr><td colspan="7" class="!py-12 text-center text-[color:var(--text-faint)] font-medium">{searchQuery || filterStatus ? 'Tidak ada unit yang cocok.' : 'Belum ada unit. Klik Tambah Unit.'}</td></tr>
				{:else}
					{#each units as unit (unit.id)}
						<tr>
							<td class="font-mono font-semibold">{unit.code}</td>
							<td class="text-sm">{unit.jenis_alat_berat_nama || '—'}</td>
							<td><span class="badge text-white" style="background-color:{statusHex(unit.status)};border-color:{statusHex(unit.status)}">{unit.status}</span></td>
							<td>
								<div class="flex items-center gap-2">
									<div class="w-14 h-1.5 rounded-full bg-[color:var(--surface-3)] overflow-hidden"><div class="h-full rounded-full" style="width:{unit.health}%;background-color:{statusHex(unit.status)}"></div></div>
									<span class="font-mono font-semibold text-sm">{unit.health}%</span>
								</div>
							</td>
							<td class="text-xs text-[color:var(--text-muted)]">{unit.maintenance}</td>
							<td class="font-mono font-semibold text-sm {unit.savings >= 0 ? 'text-healthy' : 'text-critical'}">{unit.savings >= 0 ? '+$' : '-$'}{Math.abs(unit.savings).toLocaleString()}</td>
							<td>
								<div class="flex gap-2 flex-wrap">
									<button class="btn btn-ghost !px-3 !py-1.5 text-xs" onclick={() => openDetail(unit)}>Lihat</button>
									<button class="btn btn-ghost !px-3 !py-1.5 text-xs" onclick={() => openEdit(unit)}>Edit</button>
									<button class="btn btn-danger !px-3 !py-1.5 text-xs" onclick={() => remove(unit)}>Hapus</button>
								</div>
							</td>
						</tr>
					{/each}
				{/if}
			</tbody>
		</table>
	</div>

	<!-- Pagination -->
	<div class="px-5 py-4 border-t border-[color:var(--border)] bg-[color:var(--surface-2)] flex justify-between items-center flex-wrap gap-3">
		<span class="text-sm text-[color:var(--text-muted)] font-medium">Total: <span class="font-mono font-semibold">{total}</span> unit</span>
		{#if totalPages > 1}
			<div class="flex gap-1.5">
				<button class="mini-pg" disabled={currentPage === 1} onclick={() => gotoPage(1)}>«</button>
				<button class="mini-pg" disabled={currentPage === 1} onclick={() => gotoPage(currentPage - 1)}>‹</button>
				{#each visiblePages as p (p)}
					<button class="mini-pg" class:!bg-amber={p === currentPage} class:!border-amber={p === currentPage} class:!text-graphite-900={p === currentPage} onclick={() => gotoPage(p)}>{p}</button>
				{/each}
				<button class="mini-pg" disabled={currentPage === totalPages} onclick={() => gotoPage(currentPage + 1)}>›</button>
				<button class="mini-pg" disabled={currentPage === totalPages} onclick={() => gotoPage(totalPages)}>»</button>
			</div>
		{/if}
	</div>
</section>

<!-- Peta Sebaran Sensor -->
<section class="panel p-6 mt-7">
	<div class="flex justify-between items-center mb-5 pb-4 border-b border-[color:var(--border)] flex-wrap gap-3">
		<div>
			<h2 class="font-display text-2xl font-bold uppercase tracking-wide">Peta Sebaran Sensor</h2>
			<p class="text-xs text-[color:var(--text-muted)] mt-1">Posisi unit berdasarkan koordinat (lat/long) riil · {mapUnitCount} unit terpetakan</p>
		</div>
		<div class="flex items-center gap-3 flex-wrap">
			<div class="hidden sm:flex gap-4 text-xs font-semibold">
				<div class="flex items-center gap-1.5"><span class="w-2.5 h-2.5 rounded-full bg-healthy"></span> Sehat</div>
				<div class="flex items-center gap-1.5"><span class="w-2.5 h-2.5 rounded-full bg-warning"></span> Warning</div>
				<div class="flex items-center gap-1.5"><span class="w-2.5 h-2.5 rounded-full bg-critical"></span> Critical</div>
			</div>
			<button class="btn btn-ghost !py-2 text-sm" onclick={openMapFullscreen}>
				<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2"><path d="M4 8V4h4M16 4h4v4M20 16v4h-4M8 20H4v-4" /></svg>
				Layar Penuh
			</button>
		</div>
	</div>
	<div class="relative w-full rounded-xl border border-[color:var(--border)] overflow-hidden isolate z-0" style="height:460px;">
		<div id="sensor-map" class="w-full h-full bg-[color:var(--surface-3)]"></div>
		<div class="map-depth pointer-events-none absolute inset-0 z-[400]"></div>
		{#if mapUnitCount === 0}
			<div class="absolute inset-0 z-[401] flex flex-col items-center justify-center text-center gap-2 bg-[color:var(--surface-2)]/80 backdrop-blur-sm">
				<p class="font-semibold">Belum ada unit dengan koordinat</p>
				<p class="text-sm text-[color:var(--text-muted)]">Isi Latitude &amp; Longitude saat menambah/edit unit untuk menampilkannya di peta.</p>
			</div>
		{/if}
	</div>
</section>

<!-- Detail Modal -->
{#if isDetailOpen && selectedUnit}
	<div class="fixed inset-0 z-50 flex items-center justify-center p-4" role="presentation">
		<div class="modal-backdrop" onclick={() => (isDetailOpen = false)} role="presentation"></div>
		<div class="modal-card w-full max-w-2xl flex flex-col max-h-[90vh] anim-pop">
			<div class="flex justify-between items-center px-6 py-4 border-b border-[color:var(--border)] bg-[color:var(--surface-2)]">
				<h3 class="font-display text-2xl font-bold uppercase tracking-wide">Detail Unit</h3>
				<button class="w-9 h-9 rounded-lg hover:bg-critical/15 hover:text-critical text-[color:var(--text-muted)] flex items-center justify-center transition-colors" onclick={() => (isDetailOpen = false)}>✕</button>
			</div>
			<div class="p-6 overflow-y-auto">
				<div class="flex flex-col md:flex-row gap-6 mb-6">
					<div class="w-full md:w-1/2 rounded-xl border border-[color:var(--border)] bg-steel-gradient flex items-center justify-center relative overflow-hidden" style="min-height:200px;">
						<model-viewer
							src={resolveModel(selectedUnit.model3d_url, selectedUnit.jenis_alat_berat_nama)}
							alt="Model 3D unit alat berat"
							camera-controls
							auto-rotate
							auto-rotate-delay="0"
							rotation-per-second="35deg"
							shadow-intensity="1.4"
							exposure="1.1"
							environment-image="neutral"
							interaction-prompt="none"
							style="width:100%;height:100%;min-height:200px;outline:none;background-color:transparent;"
						></model-viewer>
						<div class="absolute top-2 left-2 bg-steel/90 text-white text-[9px] font-semibold px-2 py-0.5 rounded-full pointer-events-none">● LIVE 3D</div>
						<div class="absolute bottom-2 right-2 bg-graphite-900/80 text-graphite-100 text-[9px] font-medium px-2 py-0.5 rounded-full pointer-events-none">DRAG 360°</div>
					</div>
					<div class="w-full md:w-1/2 flex flex-col gap-4 justify-center">
						<div><p class="label">Kode Unik</p><p class="text-2xl font-mono font-bold">{selectedUnit.code}</p></div>
						<div><p class="label">Jenis Alat Berat</p><p class="text-lg font-semibold">{selectedUnit.jenis_alat_berat_nama || '—'}</p></div>
						<div><span class="badge text-white" style="background-color:{statusHex(selectedUnit.status)};border-color:{statusHex(selectedUnit.status)}">Status: {selectedUnit.status}</span></div>
					</div>
				</div>
				<div class="grid grid-cols-3 gap-4 border-t border-[color:var(--border)] pt-6">
					<div class="panel-flat p-4 text-center"><p class="label">Health Score</p><p class="text-3xl font-display font-bold" style="color:{statusHex(selectedUnit.status)}">{selectedUnit.health}%</p></div>
					<div class="panel-flat p-4 text-center"><p class="label">Jadwal MTC</p><p class="text-base font-semibold mt-1 leading-tight">{selectedUnit.maintenance}</p></div>
					<div class="p-4 text-center rounded-[10px] bg-steel-gradient text-white border border-[color:var(--border)]">
						<p class="text-[10px] font-semibold uppercase tracking-wider text-graphite-300 mb-1">Est. Saving</p>
						<p class="text-xl font-mono font-bold {selectedUnit.savings >= 0 ? 'text-amber' : 'text-critical'}">{selectedUnit.savings >= 0 ? '+$' : '-$'}{Math.abs(selectedUnit.savings).toLocaleString()}</p>
					</div>
				</div>
			</div>
		</div>
	</div>
{/if}

<!-- Form Modal -->
{#if isFormOpen}
	<div class="fixed inset-0 z-50 flex items-center justify-center p-4" role="presentation">
		<div class="modal-backdrop" onclick={() => (isFormOpen = false)} role="presentation"></div>
		<div class="modal-card w-full max-w-lg flex flex-col max-h-[90vh] anim-pop">
			<div class="flex justify-between items-center px-6 py-4 border-b border-[color:var(--border)] bg-[color:var(--surface-2)]">
				<h3 class="font-display text-2xl font-bold uppercase tracking-wide">{formMode === 'add' ? 'Tambah Unit' : 'Edit Unit'}</h3>
				<button class="w-9 h-9 rounded-lg hover:bg-critical/15 hover:text-critical text-[color:var(--text-muted)] flex items-center justify-center transition-colors" onclick={() => (isFormOpen = false)}>✕</button>
			</div>
			<div class="p-6 overflow-y-auto flex flex-col gap-4">
				{#if formError}<div class="px-4 py-2.5 rounded-lg bg-critical/10 border border-critical/40 text-critical font-semibold text-sm">{formError}</div>{/if}
				<div>
					<label class="label" for="f-code">Kode Unik <span class="text-critical">*</span></label>
					<input id="f-code" bind:value={formData.code} type="text" placeholder="Cth: EXC-320-05" class="field" />
				</div>
				<div>
					<label class="label" for="f-jenis">Jenis Alat Berat <span class="text-critical">*</span></label>
					<select id="f-jenis" bind:value={formData.jenis_alat_berat_id} class="field cursor-pointer">
						<option value="">— Pilih Jenis —</option>
						{#each jenisOptions as j (j.id)}<option value={j.id}>{j.nama}</option>{/each}
					</select>
				</div>
				<div class="grid grid-cols-2 gap-4">
					<div>
						<label class="label" for="f-status">Status</label>
						<select id="f-status" bind:value={formData.status} class="field cursor-pointer">
							{#each statusOptions as s (s)}<option value={s}>{s}</option>{/each}
						</select>
					</div>
					<div>
						<label class="label" for="f-health">Health (%)</label>
						<input id="f-health" type="number" min="0" max="100" bind:value={formData.health} class="field" />
					</div>
				</div>
				<div>
					<label class="label" for="f-mtc">Jadwal Maintenance <span class="text-critical">*</span></label>
					<input id="f-mtc" bind:value={formData.maintenance} type="text" placeholder="Cth: 50 Jam Lagi" class="field" />
				</div>
				<div>
					<label class="label" for="f-savings">Est. Savings ($)</label>
					<input id="f-savings" type="number" bind:value={formData.savings} class="field" />
				</div>
				<div class="grid grid-cols-2 gap-4">
					<div>
						<label class="label" for="f-lat">Latitude</label>
						<input id="f-lat" type="number" step="0.0001" placeholder="-0.5032" bind:value={formData.lat} class="field" />
					</div>
					<div>
						<label class="label" for="f-lng">Longitude</label>
						<input id="f-lng" type="number" step="0.0001" placeholder="117.1536" bind:value={formData.lng} class="field" />
					</div>
				</div>
				<p class="text-[10px] text-[color:var(--text-faint)] -mt-2">Koordinat dipakai untuk Peta Sebaran Sensor.</p>
				<div>
					<label class="label" for="f-img">URL Gambar</label>
					<input id="f-img" bind:value={formData.img_url} type="text" placeholder="https://..." class="field text-sm" />
				</div>
				<div>
					<p class="label">Model 3D Unit (.glb / .gltf)</p>
					<div class="inline-flex p-1 rounded-lg bg-[color:var(--surface-3)] border border-[color:var(--border)] mb-3">
						<button type="button" class="px-4 py-1.5 rounded-md text-xs font-semibold transition-all {model3dMode === 'link' ? 'bg-[color:var(--surface)] text-[color:var(--text)]' : 'text-[color:var(--text-muted)]'}" onclick={() => (model3dMode = 'link')}>🔗 Link</button>
						<button type="button" class="px-4 py-1.5 rounded-md text-xs font-semibold transition-all {model3dMode === 'upload' ? 'bg-[color:var(--surface)] text-[color:var(--text)]' : 'text-[color:var(--text-muted)]'}" onclick={() => (model3dMode = 'upload')}>⬆️ Upload File</button>
					</div>

					{#if model3dMode === 'link'}
						<input bind:value={formData.model3d_url} type="text" placeholder="https://....glb" class="field text-sm" />
						<p class="text-[10px] text-[color:var(--text-faint)] mt-1.5">Tempel URL file GLB/GLTF. Kosongkan untuk pakai gambar biasa.</p>
					{:else}
						<label for="f-model-file" class="flex items-center justify-center gap-2 w-full px-4 py-4 rounded-lg border border-dashed border-[color:var(--border-strong)] bg-[color:var(--surface-2)] cursor-pointer hover:border-amber transition-colors">
							<svg class="w-5 h-5 text-[color:var(--text-muted)]" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2"><path d="M12 3v12m0 0l-4-4m4 4l4-4M4 21h16" /></svg>
							<span class="text-sm font-semibold text-[color:var(--text-muted)]">{modelUploading ? 'Mengunggah…' : 'Pilih file .glb / .gltf'}</span>
							<input id="f-model-file" type="file" accept=".glb,.gltf,model/gltf-binary" class="hidden" onchange={onModelFileChange} disabled={modelUploading} />
						</label>
						{#if modelFileName}
							<p class="text-[11px] text-healthy font-semibold mt-2 flex items-center gap-1.5">
								<svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2.5"><path d="M5 13l4 4L19 7" /></svg>
								{modelFileName}
							</p>
						{/if}
						<p class="text-[10px] text-[color:var(--text-faint)] mt-1.5">File disimpan di media (maks 50 MB).</p>
					{/if}
				</div>
			</div>
			<div class="px-6 py-4 border-t border-[color:var(--border)] bg-[color:var(--surface-2)] flex justify-end gap-3">
				<button class="btn btn-ghost px-6" onclick={() => (isFormOpen = false)}>Batal</button>
				<button class="btn btn-amber px-6 disabled:opacity-60" onclick={save} disabled={formLoading}>{formLoading ? 'Menyimpan…' : 'Simpan'}</button>
			</div>
		</div>
	</div>
{/if}

<!-- Export Modal -->
{#if isExportOpen}
	<div class="fixed inset-0 z-50 flex items-center justify-center p-4" role="presentation">
		<div class="modal-backdrop" onclick={() => (isExportOpen = false)} role="presentation"></div>
		<div class="modal-card w-full max-w-md p-8 text-center anim-pop">
			<div class="w-14 h-14 rounded-2xl bg-amber/15 border border-amber/40 flex items-center justify-center mx-auto mb-4 text-amber">
				<svg class="w-7 h-7" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2"><path d="M12 3v12m0 0l-4-4m4 4l4-4M4 21h16" /></svg>
			</div>
			<h3 class="font-display text-2xl font-bold uppercase tracking-wide mb-2">Ekspor Data</h3>
			<p class="text-[color:var(--text-muted)] mb-6">Pilih format file untuk mengunduh data unit tambang.</p>
			<button class="btn btn-ghost w-full !py-4 justify-between" onclick={exportCSV}>
				<span class="font-semibold">Ekspor sebagai CSV</span>
				<span class="text-xl">📄</span>
			</button>
			<button class="mt-5 text-sm font-semibold text-[color:var(--text-muted)] hover:text-amber transition-colors" onclick={() => (isExportOpen = false)}>Tutup</button>
		</div>
	</div>
{/if}

<!-- Fullscreen Map Modal -->
{#if isMapFullscreen}
	<div class="fixed inset-0 z-[120] flex flex-col p-4 md:p-6" role="presentation">
		<div class="modal-backdrop" onclick={closeMapFullscreen} role="presentation"></div>
		<div class="modal-card relative z-10 flex flex-col flex-1 w-full max-w-[1500px] mx-auto overflow-hidden">
			<div class="flex justify-between items-center px-6 py-4 border-b border-[color:var(--border)] bg-[color:var(--surface-2)]">
				<div>
					<h3 class="font-display text-2xl font-bold uppercase tracking-wide">Peta Sebaran Sensor</h3>
					<p class="text-xs text-[color:var(--text-muted)]">{mapUnitCount} unit · koordinat real-time</p>
				</div>
				<button class="w-9 h-9 rounded-lg hover:bg-critical/15 hover:text-critical text-[color:var(--text-muted)] flex items-center justify-center transition-colors" onclick={closeMapFullscreen}>✕</button>
			</div>
			<div class="relative flex-1">
				<div id="sensor-map-full" class="absolute inset-0 bg-[color:var(--surface-3)]"></div>
				<div class="map-depth pointer-events-none absolute inset-0 z-[400]"></div>
			</div>
		</div>
	</div>
{/if}
