<script lang="ts">
	import { onMount } from 'svelte';
	import { api } from '$lib/api';
	import { resolveModel } from '$lib/models';

	let items = $state<any[]>([]);
	let jenisList = $state<any[]>([]);
	let loading = $state(true);
	let page = $state(1);
	const perPage = 10;
	let total = $state(0);
	let totalPages = $state(1);
	let search = $state('');
	let statusFilter = $state('');
	let error = $state('');
	let toast = $state<{ ok: boolean; msg: string } | null>(null);

	let modalOpen = $state(false);
	let editing = $state<any>(null);
	let saving = $state(false);
	let uploadProgress = $state('');
	let pageNumbers = $derived.by(() => {
		const out: number[] = [];
		const start = Math.max(1, page - 2);
		const end = Math.min(totalPages, start + 4);
		for (let i = start; i <= end; i++) out.push(i);
		return out;
	});

	let form = $state<any>({
		code: '',
		jenis_alat_berat_id: '',
		status: 'SEHAT',
		health: 100,
		maintenance: '-',
		savings: 0,
		img_url: '',
		model3d_url: '',
		lat: null,
		lng: null
	});

	const statuses = ['SEHAT', 'WARNING', 'CRITICAL', 'RUSAK'];
	function statusHex(s: string) {
		return { SEHAT: '#1FA971', WARNING: '#E0A106', CRITICAL: '#E0413E', RUSAK: '#7A848E' }[s] || '#7A848E';
	}

	function notify(ok: boolean, msg: string) {
		toast = { ok, msg };
		setTimeout(() => (toast = null), 3500);
	}

	async function load() {
		loading = true;
		error = '';
		try {
			const res: any = await api.getUnitTambang({
				page,
				per_page: perPage,
				search,
				status: statusFilter || undefined
			});
			items = res.data.data;
			total = res.data.total;
			totalPages = res.data.total_pages || 1;
		} catch (e: any) {
			error = e?.message || 'Gagal memuat data';
		} finally {
			loading = false;
		}
	}

	async function loadJenis() {
		const res: any = await api.getJenisAlatBerat({ per_page: 100 });
		jenisList = res.data.data;
	}

	function openCreate() {
		editing = null;
		form = { code: '', jenis_alat_berat_id: jenisList[0]?.id || '', status: 'SEHAT', health: 100, maintenance: '-', savings: 0, img_url: '', model3d_url: '', lat: null, lng: null };
		modalOpen = true;
	}
	function openEdit(item: any) {
		editing = item;
		form = {
			code: item.code,
			jenis_alat_berat_id: item.jenis_alat_berat_id,
			status: item.status,
			health: item.health,
			maintenance: item.maintenance,
			savings: item.savings,
			img_url: item.img_url || '',
			model3d_url: item.model3d_url || '',
			lat: item.lat,
			lng: item.lng
		};
		modalOpen = true;
	}

	async function save(e: Event) {
		e.preventDefault();
		saving = true;
		try {
			const body: any = {
				...form,
				health: Number(form.health),
				savings: Number(form.savings),
				lat: form.lat === '' || form.lat === null ? null : Number(form.lat),
				lng: form.lng === '' || form.lng === null ? null : Number(form.lng),
				img_url: form.img_url || null,
				model3d_url: form.model3d_url || null
			};
			if (editing) {
				await api.updateUnitTambang(editing.id, body);
				notify(true, 'Berhasil diperbarui');
			} else {
				await api.createUnitTambang(body);
				notify(true, 'Berhasil ditambahkan');
			}
			modalOpen = false;
			await load();
		} catch (e: any) {
			notify(false, e?.message || 'Gagal menyimpan');
		} finally {
			saving = false;
		}
	}

	async function remove(item: any) {
		if (!confirm(`Hapus unit "${item.code}"?`)) return;
		try {
			await api.deleteUnitTambang(item.id);
			notify(true, 'Berhasil dihapus');
			await load();
		} catch (e: any) {
			notify(false, e?.message || 'Gagal menghapus');
		}
	}

	async function handleModelUpload(e: Event) {
		const input = e.target as HTMLInputElement;
		const file = input.files?.[0];
		if (!file) return;
		uploadProgress = 'Mengunggah…';
		try {
			const res: any = await api.uploadModel(file);
			if (res.status === 'success') {
				form.model3d_url = res.url;
				uploadProgress = '✓ Model diunggah';
			} else {
				uploadProgress = res.message || 'Gagal unggah';
			}
		} catch (err: any) {
			uploadProgress = err?.message || 'Gagal unggah';
		}
	}

	onMount(async () => {
		await loadJenis();
		await load();
	});
</script>

<svelte:head><title>Unit Tambang — Pratyaksa</title></svelte:head>

<header class="flex justify-between items-start mb-8 gap-4 flex-wrap">
	<div>
		<h1 class="font-display text-4xl md:text-5xl font-bold uppercase tracking-wide leading-none">Unit Tambang</h1>
		<p class="mt-2 text-[color:var(--text-muted)]">Kelola seluruh unit armada alat berat beserta koordinatnya.</p>
	</div>
	<button class="btn btn-amber" onclick={openCreate}>+ Tambah Unit</button>
</header>

<div class="panel p-6">
	<div class="flex gap-3 mb-5 flex-wrap">
		<input bind:value={search} placeholder="Cari kode / jenis…" class="field" style="max-width:280px;" onchange={() => { page = 1; load(); }} />
		<select bind:value={statusFilter} class="field" style="max-width:200px;" onchange={() => { page = 1; load(); }}>
			<option value="">Semua Status</option>
			{#each statuses as s (s)}<option value={s}>{s}</option>{/each}
		</select>
		<button class="btn btn-ghost" onclick={() => { page = 1; load(); }}>Terapkan</button>
	</div>

	{#if toast}
		<div class="mb-4 px-4 py-2.5 rounded-lg text-sm font-semibold {toast.ok ? 'bg-healthy/10 text-healthy border border-healthy/30' : 'bg-critical/10 text-critical border border-critical/40'}">{toast.msg}</div>
	{/if}
	{#if error}
		<div class="mb-4 px-4 py-2.5 rounded-lg bg-critical/10 border border-critical/40 text-critical text-sm">{error}</div>
	{/if}

	<div class="overflow-x-auto">
		<table class="table-industrial">
			<thead>
				<tr><th>Kode</th><th>Jenis</th><th>Status</th><th>Health</th><th>Savings</th><th class="text-right">Aksi</th></tr>
			</thead>
			<tbody>
				{#if loading}
					{#each Array(5) as _, i (i)}<tr><td colspan="6"><div class="h-4 shimmer rounded my-1"></div></td></tr>{/each}
				{:else if items.length === 0}
					<tr><td colspan="6" class="text-center text-[color:var(--text-muted)] py-10">Belum ada data.</td></tr>
				{:else}
					{#each items as item (item.id)}
						<tr>
							<td class="font-semibold">{item.code}</td>
							<td class="text-[color:var(--text-muted)]">{item.jenis_alat_berat_nama || '-'}</td>
							<td><span class="badge" style="color:{statusHex(item.status)};border-color:{statusHex(item.status)}55">{item.status}</span></td>
							<td>
								<div class="flex items-center gap-2">
									<div class="w-20 h-1.5 rounded-full bg-[color:var(--surface-3)] overflow-hidden">
										<div class="h-full rounded-full" style="width:{item.health}%;background:{statusHex(item.status)}"></div>
									</div>
									<span class="text-xs font-mono">{item.health}%</span>
								</div>
							</td>
							<td class="font-mono text-sm">${item.savings.toLocaleString()}</td>
							<td class="text-right whitespace-nowrap">
								<button class="btn btn-ghost !py-1.5 !px-3 text-xs" onclick={() => openEdit(item)}>Edit</button>
								<button class="btn btn-danger !py-1.5 !px-3 text-xs ml-2" onclick={() => remove(item)}>Hapus</button>
							</td>
						</tr>
					{/each}
				{/if}
			</tbody>
		</table>
	</div>

	<div class="flex items-center justify-between mt-5">
		<span class="text-xs text-[color:var(--text-muted)]">Total {total} data</span>
		<div class="flex items-center gap-1.5">
			<button class="mini-pg" disabled={page <= 1} onclick={() => { page--; load(); }}>‹</button>
			{#each pageNumbers as p (p)}
				<button class="mini-pg" class:!bg-amber={p === page} class:!text-graphite-900={p === page} onclick={() => { page = p; load(); }}>{p}</button>
			{/each}
			<button class="mini-pg" disabled={page >= totalPages} onclick={() => { page++; load(); }}>›</button>
		</div>
	</div>
</div>

{#if modalOpen}
	<div class="fixed inset-0 z-[100] flex items-center justify-center p-4 overflow-y-auto" role="presentation">
		<div class="modal-backdrop" onclick={() => (modalOpen = false)} role="presentation"></div>
		<div class="modal-card w-full max-w-2xl my-8">
			<div class="h-1.5 hazard-stripe opacity-90"></div>
			<form onsubmit={save} class="p-6 space-y-5">
				<h3 class="font-display text-2xl font-bold uppercase">{editing ? 'Edit' : 'Tambah'} Unit Tambang</h3>
				<div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
					<div>
						<label for="code" class="label">Kode Unit</label>
						<input id="code" bind:value={form.code} class="field" required minlength="2" maxlength="50" />
					</div>
					<div>
						<label for="jenis" class="label">Jenis Alat Berat</label>
						<select id="jenis" bind:value={form.jenis_alat_berat_id} class="field" required>
							{#each jenisList as j (j.id)}<option value={j.id}>{j.nama}</option>{/each}
						</select>
					</div>
					<div>
						<label for="status" class="label">Status</label>
						<select id="status" bind:value={form.status} class="field">
							{#each statuses as s (s)}<option value={s}>{s}</option>{/each}
						</select>
					</div>
					<div>
						<label for="health" class="label">Health (0-100)</label>
						<input id="health" type="number" min="0" max="100" bind:value={form.health} class="field" />
					</div>
					<div>
						<label for="maintenance" class="label">Maintenance</label>
						<input id="maintenance" bind:value={form.maintenance} class="field" required />
					</div>
					<div>
						<label for="savings" class="label">Savings ($)</label>
						<input id="savings" type="number" bind:value={form.savings} class="field" />
					</div>
					<div>
						<label for="lat" class="label">Latitude</label>
						<input id="lat" type="number" step="0.0001" bind:value={form.lat} class="field" />
					</div>
					<div>
						<label for="lng" class="label">Longitude</label>
						<input id="lng" type="number" step="0.0001" bind:value={form.lng} class="field" />
					</div>
				</div>
				<div>
					<label for="img_url" class="label">URL Gambar (opsional)</label>
					<input id="img_url" bind:value={form.img_url} class="field" placeholder="https://…" />
				</div>
				<div>
					<label for="model" class="label">Model 3D (.glb/.gltf)</label>
					<div class="flex items-center gap-3">
						<input id="model" type="file" accept=".glb,.gltf" class="field" onchange={handleModelUpload} />
						{#if form.model3d_url}
							<button type="button" class="btn btn-ghost !py-2 !px-3 text-xs" onclick={() => (form.model3d_url = '')}>Hapus</button>
						{/if}
					</div>
					{#if uploadProgress}<p class="text-xs text-[color:var(--text-muted)] mt-1">{uploadProgress}</p>{/if}
					{#if form.model3d_url}
						<div class="mt-3 h-40 rounded-xl overflow-hidden border border-[color:var(--border)]" style="background:linear-gradient(135deg,#2c3643,#141a21)">
							<model-viewer src={resolveModel(form.model3d_url, null)} camera-controls auto-rotate style="width:100%;height:100%;background:transparent;" interaction-prompt="none"></model-viewer>
						</div>
					{/if}
				</div>
				<div class="flex justify-end gap-3">
					<button type="button" class="btn btn-ghost" onclick={() => (modalOpen = false)}>Batal</button>
					<button type="submit" class="btn btn-amber" disabled={saving}>{saving ? 'Menyimpan…' : 'Simpan'}</button>
				</div>
			</form>
		</div>
	</div>
{/if}
