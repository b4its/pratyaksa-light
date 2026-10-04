<script lang="ts">
	import { onMount } from 'svelte';
	import { api } from '$lib/api';
	import { toast } from '$lib/stores/toast.svelte';
	import { confirmDialog } from '$lib/stores/confirm.svelte';
	import PageHeader from '$lib/components/PageHeader.svelte';
	import Modal from '$lib/components/Modal.svelte';

	let items = $state<any[]>([]);
	let loading = $state(true);
	let page = $state(1);
	const perPage = 5;
	let total = $state(0);
	let totalPages = $state(1);
	let search = $state('');
	let error = $state('');
	let lastUpdate = $state('');

	let modalOpen = $state(false);
	let editing = $state<any>(null);
	let form = $state({ nama: '', deskripsi: '' });
	let formError = $state('');
	let saving = $state(false);

	let detailOpen = $state(false);
	let selectedItem = $state<any>(null);

	const pageNumbers = $derived.by(() => {
		const out: number[] = [];
		const max = 3;
		const tp = totalPages;
		const cp = page;
		if (tp <= max) {
			for (let i = 1; i <= tp; i++) out.push(i);
			return out;
		}
		let start = Math.max(1, cp - 1);
		const end = Math.min(tp, start + max - 1);
		if (end === tp) start = Math.max(1, tp - max + 1);
		for (let i = start; i <= end; i++) out.push(i);
		return out;
	});

	function formatDate(iso: string) {
		return new Date(iso).toLocaleDateString('id-ID', { day: 'numeric', month: 'short', year: 'numeric' });
	}

	async function load() {
		loading = true;
		error = '';
		try {
			const res: any = await api.getJenisAlatBerat({ page, per_page: perPage, search: search || undefined });
			items = res.data.data;
			total = res.data.total;
			totalPages = res.data.total_pages || 1;
			lastUpdate = new Date().toLocaleTimeString('id-ID');
		} catch (e: any) {
			error = e?.message || 'Gagal memuat data.';
		} finally {
			loading = false;
		}
	}

	function onSearch() {
		page = 1;
		load();
	}

	function openCreate() {
		editing = null;
		form = { nama: '', deskripsi: '' };
		formError = '';
		modalOpen = true;
	}
	function openEdit(item: any) {
		editing = item;
		form = { nama: item.nama, deskripsi: item.deskripsi || '' };
		formError = '';
		modalOpen = true;
	}
	function openDetail(item: any) {
		selectedItem = item;
		detailOpen = true;
	}

	async function save() {
		if (!form.nama.trim()) {
			formError = 'Nama wajib diisi.';
			return;
		}
		if (form.nama.trim().length < 2) {
			formError = 'Nama minimal 2 karakter.';
			return;
		}
		if (form.nama.trim().length > 200) {
			formError = 'Nama maksimal 200 karakter.';
			return;
		}
		saving = true;
		formError = '';
		try {
			if (editing) {
				await api.updateJenisAlatBerat(editing.id, { nama: form.nama, deskripsi: form.deskripsi || undefined });
			} else {
				await api.createJenisAlatBerat({ nama: form.nama, deskripsi: form.deskripsi || undefined });
			}
			modalOpen = false;
			await load();
			toast.success(editing ? 'Jenis alat berat berhasil diperbarui.' : 'Jenis alat berat berhasil ditambahkan.');
		} catch (e: any) {
			formError = e?.message || 'Gagal menyimpan.';
		} finally {
			saving = false;
		}
	}

	async function remove(item: any) {
		const ok = await confirmDialog.ask({
			title: 'Hapus Jenis',
			message: `Hapus "${item.nama}"? Tindakan ini tidak dapat dibatalkan.`,
			confirmLabel: 'Hapus'
		});
		if (!ok) return;
		try {
			await api.deleteJenisAlatBerat(item.id);
			// Jika halaman terakhir menjadi kosong setelah hapus, mundur satu halaman.
			if (page > 1 && items.length === 1) page -= 1;
			await load();
			toast.success('Jenis alat berat berhasil dihapus.');
		} catch (e: any) {
			toast.error(e?.message || 'Gagal menghapus.');
		}
	}

	onMount(() => {
		load();
	});
</script>

<svelte:head><title>Jenis Alat Berat — Pratyaksa</title></svelte:head>

<PageHeader title="Jenis Alat Berat" subtitle="Daftar kategori alat berat yang terdaftar di sistem." {lastUpdate} />

{#if error}<div class="mb-6 px-4 py-3 rounded-xl bg-critical/10 border border-critical/40 text-critical font-semibold flex items-center gap-2">⚠️ {error}</div>{/if}

<div class="flex justify-between items-center mb-6 gap-3 flex-wrap">
	<div class="flex gap-3 flex-1 flex-wrap">
		<div class="relative flex-1" style="min-width:12rem;">
			<svg class="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-[color:var(--text-faint)]" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2"><circle cx="11" cy="11" r="8" /><path d="m21 21-4.3-4.3" /></svg>
			<input bind:value={search} onkeyup={(e) => e.key === 'Enter' && onSearch()} type="text" placeholder="Cari jenis alat berat..." class="field !pl-9" />
		</div>
		<button class="btn btn-ghost px-6" onclick={onSearch}>Cari</button>
	</div>
	<button class="btn btn-amber px-5" onclick={openCreate}>
		<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2.5"><path d="M12 5v14M5 12h14" /></svg>
		Tambah Jenis
	</button>
</div>

<section class="panel-raised overflow-hidden">
	<div class="overflow-x-auto">
		<table class="table-industrial">
			<thead>
				<tr><th>Nama Jenis</th><th>Deskripsi</th><th>Dibuat</th><th>Aksi</th></tr>
			</thead>
			<tbody>
				{#if loading}
					{#each Array(5) as _, i (i)}
						<tr>{#each Array(4) as __, j (j)}<td><div class="h-4 shimmer rounded"></div></td>{/each}</tr>
					{/each}
				{:else if items.length === 0}
					<tr><td colspan="4" class="!py-12 text-center text-[color:var(--text-faint)] font-medium">{search ? `Tidak ada hasil untuk "${search}"` : 'Belum ada data. Klik Tambah Jenis.'}</td></tr>
				{:else}
					{#each items as item (item.id)}
						<tr>
							<td class="font-semibold">{item.nama}</td>
							<td class="text-sm text-[color:var(--text-muted)]" style="max-width:20rem;">{item.deskripsi || '—'}</td>
							<td class="text-xs text-[color:var(--text-faint)] font-mono">{formatDate(item.created_at)}</td>
							<td>
								<div class="flex gap-2 flex-wrap">
									<button class="btn btn-ghost !px-3 !py-1.5 text-xs" onclick={() => openDetail(item)}>Lihat</button>
									<button class="btn btn-ghost !px-3 !py-1.5 text-xs" onclick={() => openEdit(item)}>Edit</button>
									<button class="btn btn-danger !px-3 !py-1.5 text-xs" onclick={() => remove(item)}>Hapus</button>
								</div>
							</td>
						</tr>
					{/each}
				{/if}
			</tbody>
		</table>
	</div>

	<div class="px-5 py-4 border-t border-[color:var(--border)] bg-[color:var(--surface-2)] flex justify-between items-center flex-wrap gap-3">
		<span class="text-sm text-[color:var(--text-muted)] font-medium">Total: <span class="font-mono font-semibold">{total}</span> jenis</span>
		{#if totalPages > 1}
			<div class="flex gap-1.5">
				<button class="mini-pg" aria-label="Halaman pertama" disabled={page === 1} onclick={() => { page = 1; load(); }}>«</button>
				<button class="mini-pg" aria-label="Halaman sebelumnya" disabled={page === 1} onclick={() => { page--; load(); }}>‹</button>
				{#each pageNumbers as p (p)}
					<button class="mini-pg" aria-label={`Halaman ${p}`} aria-current={p === page ? 'page' : undefined} class:!bg-amber={p === page} class:!border-amber={p === page} class:!text-graphite-900={p === page} onclick={() => { page = p; load(); }}>{p}</button>
				{/each}
				<button class="mini-pg" aria-label="Halaman berikutnya" disabled={page === totalPages} onclick={() => { page++; load(); }}>›</button>
				<button class="mini-pg" aria-label="Halaman terakhir" disabled={page === totalPages} onclick={() => { page = totalPages; load(); }}>»</button>
			</div>
		{/if}
	</div>
</section>

<!-- Detail Modal -->
{#if detailOpen && selectedItem}
	<Modal title="Detail Jenis Alat Berat" maxWidth="lg" onclose={() => (detailOpen = false)}>
		<div class="p-6 space-y-4">
			<div class="panel-flat p-4"><p class="label">Nama Jenis</p><p class="text-xl font-semibold">{selectedItem.nama}</p></div>
			<div class="panel-flat p-4"><p class="label">Deskripsi</p><p class="leading-relaxed text-[color:var(--text-muted)]">{selectedItem.deskripsi || 'Tidak ada deskripsi.'}</p></div>
			<div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
				<div class="panel-flat p-4"><p class="label">Dibuat</p><p class="font-semibold text-sm font-mono">{formatDate(selectedItem.created_at)}</p></div>
				<div class="panel-flat p-4"><p class="label">Diperbarui</p><p class="font-semibold text-sm font-mono">{formatDate(selectedItem.updated_at)}</p></div>
			</div>
		</div>
	</Modal>
{/if}

<!-- Form Modal -->
{#if modalOpen}
	<Modal title={editing ? 'Edit Jenis' : 'Tambah Jenis'} maxWidth="lg" onclose={() => (modalOpen = false)}>
		<div class="p-6 flex flex-col gap-4">
			{#if formError}<div class="px-4 py-2.5 rounded-lg bg-critical/10 border border-critical/40 text-critical font-semibold text-sm">{formError}</div>{/if}
			<div>
				<label class="label" for="j-nama">Nama Jenis <span class="text-critical">*</span></label>
				<input id="j-nama" bind:value={form.nama} type="text" placeholder="Cth: Caterpillar Excavator 320" class="field" maxlength="200" />
			</div>
			<div>
				<label class="label" for="j-desk">Deskripsi</label>
				<textarea id="j-desk" bind:value={form.deskripsi} rows="3" placeholder="Deskripsi singkat tentang jenis alat berat ini..." class="field"></textarea>
			</div>
		</div>
		<div class="px-6 py-4 border-t border-[color:var(--border)] bg-[color:var(--surface-2)] flex justify-end gap-3">
			<button class="btn btn-ghost px-6" onclick={() => (modalOpen = false)}>Batal</button>
			<button class="btn btn-amber px-6 disabled:opacity-60" onclick={save} disabled={saving}>{saving ? 'Menyimpan…' : 'Simpan'}</button>
		</div>
	</Modal>
{/if}
