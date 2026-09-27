<script lang="ts">
	import { pratyaksa } from '$lib/stores/pratyaksa.svelte';

	let switching = $state<string | null>(null);

	const modeOptions = [
		{
			id: 'simulasi' as const,
			label: 'SIMULASI',
			desc: 'Data dari simulator internal tanpa koneksi ke endpoint eksternal',
			details: ['Data deterministik dari engine Python', 'Tidak perlu koneksi jaringan', 'Cocok untuk development & demo'],
			color: 'text-warning',
			borderColor: 'border-warning/30',
			badgeClass: 'bg-warning/15 text-warning border-warning/30'
		},
		{
			id: 'live' as const,
			label: 'LIVE API',
			desc: 'Data real-time dari endpoint ML Eksternal',
			details: ['Data dari ML API via GET /fleet, /result', 'Membutuhkan koneksi ke ML API', 'Cocok untuk produksi & real monitoring'],
			color: 'text-healthy',
			borderColor: 'border-healthy/30',
			badgeClass: 'bg-healthy/15 text-healthy border-healthy/30'
		}
	];

	const activeMode = $derived((pratyaksa.status.manual_mode as 'simulasi' | 'live') || pratyaksa.status.mode);

	async function switchMode(id: 'simulasi' | 'live') {
		switching = id;
		try {
			await pratyaksa.setMode(id);
			await pratyaksa.fetchAll();
		} finally {
			switching = null;
		}
	}
</script>

<div class="panel p-5">
	<div class="flex items-center gap-2 mb-4">
		<h3 class="font-display text-lg font-bold uppercase tracking-wide">Mode Operasi</h3>
		<span class="badge {activeMode === 'live' ? 'bg-healthy/15 text-healthy border-healthy/30' : 'bg-warning/15 text-warning border-warning/30'}">
			{activeMode === 'live' ? 'LIVE' : 'SIMULASI'}
		</span>
	</div>
	<div class="grid grid-cols-1 md:grid-cols-2 gap-4">
		{#each modeOptions as m (m.id)}
			<button
				class="text-left rounded-xl border p-4 transition-all {activeMode === m.id ? m.borderColor + ' bg-[color:var(--surface-2)]' : 'border-[color:var(--border)] hover:border-[color:var(--border-strong)]'}"
				disabled={switching !== null}
				onclick={() => switchMode(m.id)}
			>
				<div class="flex items-center justify-between mb-2">
					<span class="font-bold text-sm {m.color}">{m.label}</span>
					{#if switching === m.id}
						<span class="text-[10px] text-[color:var(--text-muted)]">Menyambung…</span>
					{:else if activeMode === m.id}
						<span class="badge {m.badgeClass}">Aktif</span>
					{/if}
				</div>
				<p class="text-xs text-[color:var(--text-muted)] mb-3">{m.desc}</p>
				<ul class="text-[11px] text-[color:var(--text-faint)] space-y-1">
					{#each m.details as d (d)}
						<li>• {d}</li>
					{/each}
				</ul>
			</button>
		{/each}
	</div>
</div>
