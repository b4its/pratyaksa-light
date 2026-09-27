<script lang="ts">
	import { onMount } from 'svelte';
	import { pratyaksa } from '$lib/stores/pratyaksa.svelte';

	let {
		showSubModes = false,
		ontesttelegram
	}: { showSubModes?: boolean; ontesttelegram?: () => void } = $props();

	let menuOpen = $state(false);
	let switching = $state(false);
	let toast = $state<{ ok: boolean; msg: string } | null>(null);
	let containerRef: HTMLElement | null = $state(null);
	let toastTimer: ReturnType<typeof setTimeout> | null = null;

	const SIM_ICON = `<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M9.75 3.104v5.714a2.25 2.25 0 0 1-.659 1.591L5 14.5M9.75 3.104c-.251.023-.501.05-.75.082m.75-.082a24.301 24.301 0 0 1 4.5 0m0 0v5.714c0 .597.237 1.17.659 1.591L19.8 15.3M14.25 3.104c.251.023.501.05.75.082M19.8 15.3l-1.57.393A9.065 9.065 0 0 1 12 15a9.065 9.065 0 0 0-6.23.693L5 14.5m14.8.8 1.402 1.402c1.232 1.232.65 3.318-1.067 3.611A48.309 48.309 0 0 1 12 21c-2.773 0-5.491-.235-8.135-.687-1.718-.293-2.3-2.379-1.067-3.61L5 14.5"/></svg>`;
	const LIVE_ICON = `<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M12 21a9.004 9.004 0 0 0 8.716-6.747M12 21a9.004 9.004 0 0 1-8.716-6.747M12 21c2.485 0 4.5-4.03 4.5-9S14.485 3 12 3m0 18c-2.485 0-4.5-4.03-4.5-9S9.515 3 12 3m0 0a8.997 8.997 0 0 1 7.843 4.582M12 3a8.997 8.997 0 0 0-7.843 4.582m15.686 0A11.953 11.953 0 0 1 12 10.5c-2.998 0-5.74-1.1-7.843-2.918m15.686 0A8.959 8.959 0 0 1 21 12c0 .778-.099 1.533-.284 2.253m0 0A17.919 17.919 0 0 1 12 16.5c-3.162 0-6.133-.815-8.716-2.247m0 0A9.015 9.015 0 0 1 3 12c0-1.605.42-3.113 1.157-4.418"/></svg>`;
	const BRAIN_ICON = `<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M9 12.75 11.25 15 15 9.75m-3-7.036A11.959 11.959 0 0 1 3.598 6 11.99 11.99 0 0 0 3 9.749c0 5.592 3.824 10.29 9 11.623 5.176-1.332 9-6.03 9-11.622 0-1.31-.21-2.571-.598-3.751h-.152c-3.196 0-6.1-1.248-8.25-3.285Z"/></svg>`;
	const TG_ICON = `<svg class="w-4 h-4" fill="currentColor" viewBox="0 0 24 24"><path d="M9.78 18.65l.28-4.23 7.68-6.92c.34-.31-.07-.46-.52-.19L7.74 13.3 3.64 12c-.88-.25-.89-.86.2-1.3l15.97-6.16c.73-.33 1.43.18 1.15 1.3l-2.72 12.81c-.19.91-.74 1.13-1.5.71L12.6 16.3l-1.99 1.93c-.23.23-.42.42-.83.42z"/></svg>`;

	const branches = [
		{
			id: 'simulasi' as const,
			label: 'Live Simulasi',
			desc: 'Data dari simulator internal — tanpa koneksi eksternal',
			icon: SIM_ICON,
			header: 'Simulasi (Internal)',
			itemDesc: 'Data dari engine Python internal',
			color: 'border-warning/30 bg-warning/8 text-warning',
			activeColor: 'text-warning',
			dotColor: 'bg-warning'
		},
		{
			id: 'live' as const,
			label: 'Live API',
			desc: 'Data real-time dari 192.168.101.3:6000 — koneksi eksternal',
			icon: LIVE_ICON,
			header: 'API Eksternal (192.168.101.3:6000)',
			itemDesc: 'Data dari 192.168.101.3:6000',
			color: 'border-healthy/30 bg-healthy/8 text-healthy',
			activeColor: 'text-healthy',
			dotColor: 'bg-healthy'
		}
	];

	const subOptions = [
		{ id: 'silent' as const, label: 'Tanpa Telegram', icon: BRAIN_ICON },
		{ id: 'telegram' as const, label: '+ Kirim Telegram', icon: TG_ICON }
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
		(statusInfo.manualMode as 'simulasi' | 'live') ||
			(statusInfo.mode as 'simulasi' | 'live') ||
			'simulasi'
	);
	const activeSubId = $derived<'silent' | 'telegram'>(
		pratyaksa.sourceMode === 'live-telegram' ? 'telegram' : 'silent'
	);
	const activeBranch = $derived(branches.find((b) => b.id === activeBranchId) || branches[0]);

	const modeLabel = $derived(
		switching ? 'MENYAMBUNG...' : `${activeBranch.label} ${activeSubId === 'telegram' ? '+ TG' : ''}`
	);

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
			<span class="w-2 h-2 rounded-full bg-steel animate-spin border-2 border-transparent border-t-current"
			></span>
		{:else}
			<span
				class={['w-2 h-2 rounded-full', activeBranch?.dotColor || 'bg-warning', activeBranchId === 'live' ? 'anim-live' : ''].join(' ')}
			></span>
		{/if}
		<span>{modeLabel}</span>
		<svg class="w-3 h-3 transition-transform" class:rotate-180={menuOpen} fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2.5"
			><path d="m6 9 6 6 6-6" /></svg
		>
	</button>

	{#if menuOpen}
		<div class="absolute right-0 mt-2 w-80 z-50 panel-raised p-2 anim-pop">
			{#each branches as branch, i (branch.id)}
				<div class="mb-1">
					<div
						class="px-2 py-1 flex items-center gap-2 text-[10px] font-semibold uppercase tracking-wider text-[color:var(--text-faint)]"
					>
						<span class="w-3 h-3">{@html branch.icon}</span>
						{branch.header}
					</div>
					<button
						class={['w-full flex items-center gap-3 p-2.5 rounded-lg text-left transition-colors', activeBranchId === branch.id ? (branch.id === 'simulasi' ? 'bg-warning/10 border border-warning/30' : 'bg-healthy/10 border border-healthy/30') : 'hover:bg-[color:var(--surface-2)]'].join(' ')}
						onclick={() => switchBranch(branch.id)}
					>
						<span
							class={['w-2 h-2 rounded-full mt-0.5 shrink-0', activeBranchId === branch.id ? branch.dotColor : 'bg-[color:var(--text-faint)]'].join(' ')}
						></span>
						<span class="flex-1 min-w-0">
							<span
								class={['block text-sm font-semibold', activeBranchId === branch.id ? branch.activeColor : '']
									.join(' ')}>{branch.label}</span
							>
							<span class="block text-[10px] text-[color:var(--text-muted)]">{branch.itemDesc}</span>
						</span>
						{#if activeBranchId === branch.id}
							<svg
								class={['w-4 h-4 shrink-0', branch.activeColor].join(' ')}
								fill="none"
								stroke="currentColor"
								viewBox="0 0 24 24"
								stroke-width="2.5"><path d="M5 13l4 4L19 7" /></svg
							>
						{/if}
					</button>
					{#if activeBranchId === branch.id}
						<div class="flex gap-1.5 pl-8 mt-1.5 mb-2">
							{#each subOptions as s (s.id)}
								<button
									class={['flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg text-[11px] font-medium border transition-all', activeSubId === s.id ? (branch.id === 'simulasi' ? 'bg-warning/15 border-warning/30 text-warning' : 'bg-healthy/15 border-healthy/30 text-healthy') : 'border-[color:var(--border)] text-[color:var(--text-muted)] hover:border-[color:var(--border-strong)]'].join(' ')}
									onclick={() => switchSub(s.id)}
								>
									<span>{@html s.icon}</span>
									<span>{s.label}</span>
								</button>
							{/each}
						</div>
					{/if}
				</div>
				{#if i === 0}
					<div class="border-t border-[color:var(--border)] my-1.5"></div>
				{/if}
			{/each}

			{#if showSubModes}
				<button
					class="w-full flex items-center justify-center gap-2 mt-1 px-3 py-2 rounded-lg text-xs font-semibold border border-[color:var(--border)] text-[color:var(--text-muted)] hover:bg-[color:var(--surface-2)] transition-all"
					onclick={() => ontesttelegram?.()}
				>
					<svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2"
						><path stroke-linecap="round" stroke-linejoin="round" d="M8.29 6.293a9 9 0 1111.418 11.418M12 2a10 10 0 019.95 9M2 12h2m2-6-2-2m14 14l2 2M12 20v2m-4-2l-2 2" /></svg
					>
					Test Telegram
				</button>
			{/if}

			{#if toast}
				<div class="px-2 pt-2">
					<div
						class="px-2.5 py-1.5 rounded-lg text-[11px] font-semibold flex items-center gap-1.5 transition-all anim-pop {toast.ok
							? 'bg-healthy/15 text-healthy'
							: 'bg-critical/15 text-critical'}"
					>
						<span>{toast.msg}</span>
					</div>
				</div>
			{/if}

			<div class="border-t border-[color:var(--border)] mt-1.5 pt-2 px-2">
				<div class="flex items-center justify-between text-[10px]">
					<div class="flex items-center gap-1.5">
						<span class="font-semibold uppercase tracking-wider text-[color:var(--text-faint)]"
							>Status Backend:</span
						>
						<span class="flex items-center gap-1 {activeBranch.activeColor}">
							<span class="w-1.5 h-1.5 rounded-full {activeBranch.dotColor}"></span>
							<span class="font-bold">{activeBranch.label}</span>
						</span>
					</div>
					<div class="flex items-center gap-1 text-[color:var(--text-faint)]">
						{#if statusInfo.manualMode}
							<span class="text-amber font-semibold">(Manual)</span>
						{:else}
							<span>(Auto)</span>
						{/if}
						{#if activeBranchId === 'live'}
							<span class="flex items-center gap-1">
								·
								<span class="w-1.5 h-1.5 rounded-full {statusInfo.reachable ? 'bg-healthy' : 'bg-critical'}"
								></span>
								<span class={statusInfo.reachable ? 'text-healthy' : 'text-critical'}
									>{statusInfo.reachable ? 'Online' : 'Offline'}</span
								>
							</span>
						{/if}
					</div>
				</div>
			</div>
		</div>
	{/if}
</div>
