<script lang="ts">
	import { onMount } from 'svelte';
	import { api } from '$lib/api';

	let items = $state<any[]>([]);
	let loading = $state(true);
	let page = $state(1);
	let perPage = 10;
	let total = $state(0);
	let totalPages = $state(1);
	let search = $state('');
	let error = $state('');
	let toast = $state<{ ok: boolean; msg: string } | null>(null);

	let modalOpen = $state(false);
	let editing = $state<any>(null);
	let form = $state({ nama: '', deskripsi: '' });
	let saving = $state(false);

	const pageNumbers = $derived(() => {
		const out: number[] = [];
		const start = Math.max(1, page - 2);
		const end = Math.min(totalPages, start + 4);
		for (let i = start; i <= end; i++) out.push(i);
		return out;
	});

	function notify(ok: boolean, msg: string) {
		toast = { ok, msg };
		setTimeout(() => (toast = null), 3500);
	}

	async function load() {
		loading = true;
		error = '';
		try {
			const res: any = await api.getJenisAlatBerat({ page, per_page: perPage, search });
			items = res.data.data;
			total = res.data.total;
			totalPages = res.data.total_pages || 1;
		} catch (e: any) {
			error = e?.message || 'Gagal memuat data';
		} finally {
			loading = false;
		}
	}

	function openCreate() {
		editing = null;
		form = { nama: '', deskripsi: '' };
		modalOpen = true;
	}
	function openEdit(item: any) {
		editing = item;
		form = { nama: item.nama, deskripsi: item.deskripsi || '' };
		modalOpen = true;
	}

	async function save(e: Event) {
		e.preventDefault();
		saving = true;
		try {
			if (editing) {
				await api.updateJenisAlatBerat(editing.id, form);
				notify(true, 'Berhasil diperbarui');
			} else {
				await api.createJenisAlatBerat(form);
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
		if (!confirm(`Hapus "${item.nama}"?`)) return;
		try {
			await api.deleteJenisAlatBerat(item.id);
			notify(true, 'Berhasil dihapus');
			await load();
		} catch (e: any) {
			notify(false, e?.message || 'Gagal menghapus');
		}
	}

	function doSearch(e: Event) {
		e.preventDefault();
		page = 1;
		load();
	}

	onMount(load);
</script>

<svelte:head><title>Jenis Alat Berat — Pratyaksa</title></svelte:head>

<header class="flex justify-between items-start mb-8 gap-4 flex-wrap">
	<div>
		<h1 class="font-display text-4xl md:text-5xl font-bold uppercase tracking-wide leading-none">Jenis Alat Berat</h1>
		<p class="mt-2 text-[color:var(--text-muted)]">Master data kategori alat berat pada armada.</p>
	</div>
	<button class="btn btn-amber" onclick={openCreate}>+ Tambah Jenis</button>
</header>

<div class="panel p-6">
	<form onsubmit={doSearch} class="flex gap-3 mb-5 flex-wrap">
		<input bind:value={search} placeholder="Cari nama jenis…" class="field" style="max-width:320px;" />
		<button class="btn btn-ghost" type="submit">Cari</button>
	</form>

	{#if toast}
		<div class="mb-4 px-4 py-2.5 rounded-lg text-sm font-semibold {toast.ok ? 'bg-healthy/10 text-healthy border border-healthy/30' : 'bg-critical/10 text-critical border border-critical/40'}">
			{toast.msg}
		</div>
	{/if}
	{#if error}
		<div class="mb-4 px-4 py-2.5 rounded-lg bg-critical/10 border border-critical/40 text-critical text-sm">{error}</div>
	{/if}

	<div class="overflow-x-auto">
		<table class="table-industrial">
			<thead>
				<tr><th>Nama</th><th>Deskripsi</th><th class="text-right">Aksi</th></tr>
			</thead>
			<tbody>
				{#if loading}
					{#each Array(5) as _, i (i)}
						<tr><td colspan="3"><div class="h-4 shimmer rounded my-1"></div></td></tr>
					{/each}
				{:else if items.length === 0}
					<tr><td colspan="3" class="text-center text-[color:var(--text-muted)] py-10">Belum ada data.</td></tr>
				{:else}
					{#each items as item (item.id)}
						<tr>
							<td class="font-semibold">{item.nama}</td>
							<td class="text-[color:var(--text-muted)]">{item.deskripsi || '-'}</td>
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
			{#each pageNumbers() as p (p)}
				<button class="mini-pg" class:!bg-amber={p === page} class:!text-graphite-900={p === page} onclick={() => { page = p; load(); }}>{p}</button>
			{/each}
			<button class="mini-pg" disabled={page >= totalPages} onclick={() => { page++; load(); }}>›</button>
		</div>
	</div>
</div>

{#if modalOpen}
	<div class="fixed inset-0 z-[100] flex items-center justify-center p-4" role="presentation">
		<div class="modal-backdrop" onclick={() => (modalOpen = false)} role="presentation"></div>
		<div class="modal-card w-full max-w-md">
			<div class="h-1.5 hazard-stripe opacity-90"></div>
			<form onsubmit={save} class="p-6 space-y-5">
				<h3 class="font-display text-2xl font-bold uppercase">{editing ? 'Edit' : 'Tambah'} Jenis Alat Berat</h3>
				<div>
					<label for="nama" class="label">Nama</label>
					<input id="nama" bind:value={form.nama} class="field" required minlength="2" maxlength="200" />
				</div>
				<div>
					<label for="deskripsi" class="label">Deskripsi</label>
					<textarea id="deskripsi" bind:value={form.deskripsi} class="field" rows="3"></textarea>
				</div>
				<div class="flex justify-end gap-3">
					<button type="button" class="btn btn-ghost" onclick={() => (modalOpen = false)}>Batal</button>
					<button type="submit" class="btn btn-amber" disabled={saving}>{saving ? 'Menyimpan…' : 'Simpan'}</button>
				</div>
			</form>
		</div>
	</div>
{/if}
