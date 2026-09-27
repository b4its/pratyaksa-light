<script lang="ts">
	import { onMount } from 'svelte';
	import { pratyaksa } from '$lib/stores/pratyaksa.svelte';

	let menuOpen = $state(false);
	let switching = $state(false);
	let toast = $state<{ ok: boolean; msg: string } | null>(null);
	let containerRef: HTMLElement | null = $state(null);
	let toastTimer: ReturnType<typeof setTimeout> | null = null;

	const branches = [
		{
			id: 'simulasi' as const,
			label: 'Live Simulasi',
			desc: 'Data dari simulator internal — tanpa koneksi eksternal',
			color: 'border-warning/30 bg-warning/8 text-warning',
			dotColor: 'bg-warning'
		},
		{
			id: 'live' as const,
			label: 'Live API',
			desc: 'Data real-time dari ML API — koneksi eksternal',
			color: 'border-healthy/30 bg-healthy/8 text-healthy',
			dotColor: 'bg-healthy'
		}
	];

	const subOptions = [
		{ id: 'silent' as const, label: 'Tanpa Telegram' },
		{ id: 'telegram' as const, label: '+ Kirim Telegram' }
	];

	function showToast(ok: boolean, msg: string) {
		toast = { ok, msg };
		if (toastTimer) clearTimeout(toastTimer);
		toastTimer = setTimeout(() => (toast = null), 4000);
	}

	const statusInfo = $derived({
		mode: pratyaksa.status.mode || 'simulasi',
		manualMode: pratyaksa.status.manual_mode,
		reachable: pratyaksa.status.api_reachable
	});

	const activeBranchId = $derived<'simulasi' | 'live'>(
		(statusInfo.manualMode as 'simulasi' | 'live') || (statusInfo.mode as 'simulasi' | 'live') || 'simulasi'
	);
	const activeSubId = $derived<'silent' | 'telegram'>(
		pratyaksa.sourceMode === 'live-telegram' ? 'telegram' : 'silent'
	);
	const activeBranch = $derived(branches.find((b) => b.id === activeBranchId) || branches[0]);

	const modeLabel = $derived(() => {
		if (switching) return 'MENYAMBUNG...';
		const b = activeBranch;
		return `${b.label} ${activeSubId === 'telegram' ? '+ TG' : ''}`;
	});

	async function switchBranch(branchId: 'simulasi' | 'live') {
		if (switching) return;
		switching = true;
		try {
			await pratyaksa.setMode(branchId);
			pratyaksa.setSourceMode(activeSubId === 'telegram' ? 'live-telegram' : 'live-silent');
			await pratyaksa.fetchAll();
		} catch (e: any) {
			showToast(false, `✗ Gagal ganti mode: ${e?.message || 'backend error'}`);
		} finally {
			switching = false;
		}
	}

	function switchSub(subId: 'silent' | 'telegram') {
		pratyaksa.setSourceMode(subId === 'telegram' ? 'live-telegram' : 'live-silent');
		const label = subOptions.find((s) => s.id === subId)?.label || subId;
		showToast(true, `✓ ${label}`);
	}

	onMount(() => {
		const onClick = (e: MouseEvent) => {
			if (containerRef && !containerRef.contains(e.target as Node)) menuOpen = false;
		};
		document.addEventListener('click', onClick);
		return () => document.removeEventListener('click', onClick);
	});
</script>

<div bind:this={containerRef} class="relative">
	<button
		class={['flex items-center gap-2 px-3 py-2 rounded-xl text-xs font-semibold border transition-colors cursor-pointer whitespace-nowrap', activeBranch?.color || '', switching ? 'animate-pulse' : ''].join(' ')}
		onclick={() => (menuOpen = !menuOpen)}
	>
		{#if switching}
			<span class="w-2 h-2 rounded-full bg-steel animate-spin border-2 border-transparent border-t-current"></span>
		{:else}
			<span class={['w-2 h-2 rounded-full', activeBranch?.dotColor || 'bg-warning', activeBranchId === 'live' ? 'anim-live' : ''].join(' ')}></span>
		{/if}
		<span>{modeLabel()}</span>
		<svg class="w-3 h-3 transition-transform" class:rotate-180={menuOpen} fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2.5"
			><path d="m6 9 6 6 6-6" /></svg
		>
	</button>

	{#if menuOpen}
		<div class="absolute right-0 mt-2 w-80 z-50 panel-raised p-2 anim-pop">
			{#each branches as branch (branch.id)}
				<div class="mb-1">
					<div class="px-2 py-1 text-[10px] font-semibold uppercase tracking-wider text-[color:var(--text-faint)]">
						{branch.id === 'simulasi' ? 'Simulasi (Internal)' : 'API Eksternal'}
					</div>
					<button
						class={['w-full flex items-center gap-3 p-2.5 rounded-lg text-left transition-colors', activeBranchId === branch.id ? 'bg-warning/10 border border-warning/30' : 'hover:bg-[color:var(--surface-2)]'].join(' ')}
						onclick={() => switchBranch(branch.id)}
					>
						<span class={['w-2 h-2 rounded-full mt-0.5 shrink-0', activeBranchId === branch.id ? branch.dotColor : 'bg-[color:var(--text-faint)]'].join(' ')}></span>
						<span class="flex-1 min-w-0">
							<span class="block text-sm font-semibold">{branch.label}</span>
							<span class="block text-[10px] text-[color:var(--text-muted)]">{branch.desc}</span>
						</span>
						{#if activeBranchId === branch.id}
							<svg class="w-4 h-4 text-warning shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2.5"
								><path d="M5 13l4 4L19 7" /></svg
							>
						{/if}
					</button>
					{#if activeBranchId === branch.id}
						<div class="flex gap-1.5 pl-8 mt-1.5 mb-2">
							{#each subOptions as s (s.id)}
								<button
									class={['px-2.5 py-1.5 rounded-lg text-[11px] font-medium border transition-all', activeSubId === s.id ? 'bg-warning/15 border-warning/30 text-warning' : 'border-[color:var(--border)] text-[color:var(--text-muted)] hover:border-[color:var(--border-strong)]'].join(' ')}
									onclick={() => switchSub(s.id)}
								>
									{s.label}
								</button>
							{/each}
						</div>
					{/if}
				</div>
			{/each}

			{#if toast}
				<div class="px-2.5 py-1.5 rounded-lg text-[11px] font-semibold {toast.ok ? 'bg-healthy/10 text-healthy' : 'bg-critical/10 text-critical'}">
					{toast.msg}
				</div>
			{/if}
		</div>
	{/if}
</div>
