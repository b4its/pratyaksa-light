<script lang="ts">
	import { pratyaksa } from '$lib/stores/pratyaksa.svelte';
	import type { SourceMode } from '$lib/stores/pratyaksa.svelte';

	let {
		showSubModes = false,
		compact = false,
		ontesttelegram
	}: { showSubModes?: boolean; compact?: boolean; ontesttelegram?: () => void } = $props();

	let switching = $state(false);
	let switchingMode = $state<string | null>(null);
	let toast = $state<{ ok: boolean; msg: string } | null>(null);
	let toastTimer: ReturnType<typeof setTimeout> | null = null;

	const SIM_ICON = `<svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.5"><path stroke-linecap="round" stroke-linejoin="round" d="M9.75 3.104v5.714a2.25 2.25 0 0 1-.659 1.591L5 14.5M9.75 3.104c-.251.023-.501.05-.75.082m.75-.082a24.301 24.301 0 0 1 4.5 0m0 0v5.714c0 .597.237 1.17.659 1.591L19.8 15.3M14.25 3.104c.251.023.501.05.75.082M19.8 15.3l-1.57.393A9.065 9.065 0 0 1 12 15a9.065 9.065 0 0 0-6.23.693L5 14.5m14.8.8 1.402 1.402c1.232 1.232.65 3.318-1.067 3.611A48.309 48.309 0 0 1 12 21c-2.773 0-5.491-.235-8.135-.687-1.718-.293-2.3-2.379-1.067-3.61L5 14.5"/></svg>`;
	const LIVE_ICON = `<svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.5"><path stroke-linecap="round" stroke-linejoin="round" d="M12 21a9.004 9.004 0 0 0 8.716-6.747M12 21a9.004 9.004 0 0 1-8.716-6.747M12 21c2.485 0 4.5-4.03 4.5-9S14.485 3 12 3m0 18c-2.485 0-4.5-4.03-4.5-9S9.515 3 12 3m0 0a8.997 8.997 0 0 1 7.843 4.582M12 3a8.997 8.997 0 0 0-7.843 4.582m15.686 0A11.953 11.953 0 0 1 12 10.5c-2.998 0-5.74-1.1-7.843-2.918m15.686 0A8.959 8.959 0 0 1 21 12c0 .778-.099 1.533-.284 2.253m0 0A17.919 17.919 0 0 1 12 16.5c-3.162 0-6.133-.815-8.716-2.247m0 0A9.015 9.015 0 0 1 3 12c0-1.605.42-3.113 1.157-4.418"/></svg>`;

	const modeOptions = [
		{
			id: 'simulasi' as const,
			label: 'SIMULASI',
			icon: SIM_ICON,
			desc: 'Data dari simulator internal tanpa koneksi ke endpoint eksternal',
			details: [
				'Data deterministik dari engine Python',
				'Tidak perlu koneksi jaringan',
				'Cocok untuk development & demo'
			],
			color: 'text-warning',
			bgColor: 'bg-warning/8',
			borderColor: 'border-warning/30',
			dotColor: 'bg-warning',
			badgeClass: 'bg-warning/15 text-warning border-warning/30'
		},
		{
			id: 'live' as const,
			label: 'LIVE API',
			icon: LIVE_ICON,
			desc: 'Data real-time dari endpoint ML Eksternal (192.168.101.3:6000)',
			details: [
				'Data dari ML API via GET /fleet, /result, dll',
				'Membutuhkan koneksi ke 192.168.101.3:6000',
				'Cocok untuk produksi & real monitoring'
			],
			color: 'text-healthy',
			bgColor: 'bg-healthy/8',
			borderColor: 'border-healthy/30',
			dotColor: 'bg-healthy',
			badgeClass: 'bg-healthy/15 text-healthy border-healthy/30'
		}
	];

	interface SubModeOption {
		id: SourceMode;
		label: string;
		desc: string;
		icon: string;
		color: string;
		dotColor: string;
	}
	const BRAIN_ICON = `<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M9 12.75 11.25 15 15 9.75m-3-7.036A11.959 11.959 0 0 1 3.598 6 11.99 11.99 0 0 0 3 9.749c0 5.592 3.824 10.29 9 11.623 5.176-1.332 9-6.03 9-11.622 0-1.31-.21-2.571-.598-3.751h-.152c-3.196 0-6.1-1.248-8.25-3.285Z"/></svg>`;
	const TG_ICON = `<svg class="w-4 h-4" fill="currentColor" viewBox="0 0 24 24"><path d="M9.78 18.65l.28-4.23 7.68-6.92c.34-.31-.07-.46-.52-.19L7.74 13.3 3.64 12c-.88-.25-.89-.86.2-1.3l15.97-6.16c.73-.33 1.43.18 1.15 1.3l-2.72 12.81c-.19.91-.74 1.13-1.5.71L12.6 16.3l-1.99 1.93c-.23.23-.42.42-.83.42z"/></svg>`;
	const LINK_ICON = `<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M13.19 8.688a4.5 4.5 0 0 1 1.242 7.244l-4.5 4.5a4.5 4.5 0 0 1-6.364-6.364l1.757-1.757m13.35-.622 1.757-1.757a4.5 4.5 0 0 0-6.364-6.364l-4.5 4.5a4.5 4.5 0 0 0 1.242 7.244"/></svg>`;
	const ML_ICON = `<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M12 20V10m0 0L8 14m4-4 4 4M18 20V4M6 20v-4"/></svg>`;

	const subModeOptions: SubModeOption[] = [
		{
			id: 'live-silent',
			label: 'Live (tanpa Telegram)',
			desc: 'Monitoring real-time tanpa notifikasi',
			icon: BRAIN_ICON,
			color: 'text-healthy',
			dotColor: 'bg-healthy'
		},
		{
			id: 'live-telegram',
			label: 'Live + Kirim Telegram',
			desc: 'Alert otomatis CRITICAL & WARNING ke Telegram',
			icon: TG_ICON,
			color: 'text-steel',
			dotColor: 'bg-steel'
		},
		{
			id: 'hit-endpoint-sendiri',
			label: 'Hit Endpoint Sendiri',
			desc: 'Panggil endpoint kustom langsung dari frontend',
			icon: LINK_ICON,
			color: 'text-copper',
			dotColor: 'bg-copper'
		},
		{
			id: 'hit-endpoint-ml',
			label: 'Hit Endpoint ML',
			desc: 'Panggil endpoint ML terpisah untuk prediksi custom',
			icon: ML_ICON,
			color: 'text-amber',
			dotColor: 'bg-amber'
		}
	];

	function showToast(ok: boolean, msg: string) {
		toast = { ok, msg };
		if (toastTimer) clearTimeout(toastTimer);
		toastTimer = setTimeout(() => (toast = null), 5000);
	}

	const isLocked = $derived(pratyaksa.status.manual_mode != null);
	const currentModeId = $derived(
		(pratyaksa.status.manual_mode as 'simulasi' | 'live') || pratyaksa.status.mode || 'simulasi'
	);

	const statusInfo = $derived({
		mode: pratyaksa.status.mode || 'simulasi',
		manualMode: pratyaksa.status.manual_mode,
		reachable: pratyaksa.status.api_reachable,
		fleetCount: pratyaksa.status.fleet_count || 0
	});

	async function selectMode(id: 'simulasi' | 'live') {
		if (switching) {
			showToast(false, 'Masih dalam proses perpindahan mode, tunggu sebentar...');
			return false;
		}
		switching = true;
		switchingMode = id;
		try {
			await pratyaksa.setMode(id);
			await pratyaksa.fetchAll();
			const modeName = id === 'live' ? 'LIVE API' : 'SIMULASI';
			showToast(true, `✓ Sumber data berhasil dipilih: ${modeName}`);
			return true;
		} catch (e: any) {
			showToast(false, `✗ Gagal pilih mode: ${e?.message || 'Gagal terhubung ke backend'}`);
			return false;
		} finally {
			switching = false;
			switchingMode = null;
		}
	}

	async function setSubMode(id: SourceMode) {
		if (currentModeId !== 'live') {
			const ok = await selectMode('live');
			if (!ok) return;
		}
		pratyaksa.setSourceMode(id);
		const subName = subModeOptions.find((s) => s.id === id)?.label || id;
		showToast(true, `✓ Mode analisa: ${subName}`);
	}

	function subModeClass(sm: SubModeOption, active: boolean) {
		if (!active)
			return 'border-[color:var(--border)] text-[color:var(--text-muted)] hover:bg-[color:var(--surface-2)]';
		return `${sm.color} border-current/30 bg-current/10`;
	}
</script>

<div>
	<!-- Toast Notification -->
	{#if toast}
		<div
			class="mb-4 px-4 py-3 rounded-xl text-sm font-semibold flex items-center gap-2.5 transition-all anim-pop {toast.ok
				? 'bg-healthy/15 border border-healthy/40 text-healthy'
				: 'bg-critical/15 border border-critical/40 text-critical'}"
		>
			{#if toast.ok}
				<svg class="w-5 h-5 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2.5"
					><path stroke-linecap="round" stroke-linejoin="round" d="M9 12.75 11.25 15 15 9.75M21 12a9 9 0 1 1-18 0 9 9 0 0 1 18 0Z" /></svg
				>
			{:else}
				<svg class="w-5 h-5 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2.5"
					><path stroke-linecap="round" stroke-linejoin="round" d="M12 9v3.75m9-.75a9 9 0 1 1-18 0 9 9 0 0 1 18 0Zm-9 3.75h.008v.008H12v-.008Z" /></svg
				>
			{/if}
			<span>{toast.msg}</span>
			<button class="ml-auto opacity-60 hover:opacity-100" onclick={() => (toast = null)}>✕</button>
		</div>
	{/if}

	<!-- ── MODE LOCK TABLE (selalu tampil; compact hanya menambah pill bar) ── -->
	<div class="panel overflow-hidden mb-5">
			<div
				class="px-5 py-3 border-b border-[color:var(--border)] flex items-center justify-between flex-wrap gap-2"
			>
				<div class="flex items-center gap-2.5">
					<svg class="w-4 h-4 text-[color:var(--text-muted)]" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2"
						><path stroke-linecap="round" stroke-linejoin="round" d="M9 12.75 11.25 15 15 9.75m-3-7.036A11.959 11.959 0 0 1 3.598 6 11.99 11.99 0 0 0 3 9.749c0 5.592 3.824 10.29 9 11.623 5.176-1.332 9-6.03 9-11.622 0-1.31-.21-2.571-.598-3.751h-.152c-3.196 0-6.1-1.248-8.25-3.285Z" /></svg
					>
					<h3 class="font-semibold text-sm uppercase tracking-wider">Sumber Data</h3>
				</div>
				<div class="flex items-center gap-2">
					<span class="text-[10px] font-mono text-[color:var(--text-faint)]">
						Fleet: {statusInfo.fleetCount} unit
					</span>
					{#if isLocked}
						<span
							class="text-[10px] font-semibold px-2 py-0.5 rounded-full bg-amber/15 text-amber border border-amber/30 flex items-center gap-1"
						>
							<svg class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2.5"
								><path stroke-linecap="round" stroke-linejoin="round" d="M16.5 10.5V6.75a4.5 4.5 0 1 0-9 0v3.75m-.75 11.25h10.5a2.25 2.25 0 0 0 2.25-2.25v-6.75a2.25 2.25 0 0 0-2.25-2.25H6.75a2.25 2.25 0 0 0-2.25 2.25v6.75a2.25 2.25 0 0 0 2.25 2.25Z" /></svg
							>
							TERKUNCI
						</span>
					{:else}
						<span
							class="text-[10px] font-semibold px-2 py-0.5 rounded-full bg-steel/15 text-steel border border-steel/30 flex items-center gap-1"
						>
							<svg class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2.5"
								><path stroke-linecap="round" stroke-linejoin="round" d="M13.5 10.5V6.75a4.5 4.5 0 1 1 9 0v3.75M3.75 21.75h10.5a2.25 2.25 0 0 0 2.25-2.25v-6.75a2.25 2.25 0 0 0-2.25-2.25H3.75a2.25 2.25 0 0 0-2.25 2.25v6.75a2.25 2.25 0 0 0 2.25 2.25Z" /></svg
							>
							AUTO
						</span>
					{/if}
				</div>
			</div>

			<div class="grid grid-cols-1 md:grid-cols-2 gap-3 p-4">
				{#each modeOptions as opt (opt.id)}
					<button
						disabled={switching}
						class="relative rounded-xl border-2 p-4 text-left transition-all duration-200 disabled:opacity-70 {currentModeId ===
						opt.id
							? `${opt.borderColor} ${opt.bgColor}`
							: 'border-[color:var(--border)] hover:border-[color:var(--border-strong)] hover:bg-[color:var(--surface-2)]'} {switching &&
						switchingMode === opt.id
							? 'animate-pulse'
							: ''}"
						onclick={() => selectMode(opt.id)}
					>
						<div class="flex items-start justify-between mb-3">
							<div class="flex items-center gap-2.5">
								<span class={currentModeId === opt.id ? opt.color : 'text-[color:var(--text-muted)]'}
									>{@html opt.icon}</span
								>
								<span
									class="font-display font-bold text-lg uppercase tracking-wide {currentModeId === opt.id
										? opt.color
										: 'text-[color:var(--text)]'}">{opt.label}</span
								>
							</div>
							{#if currentModeId === opt.id}
								<span class="flex items-center gap-1 text-[10px] font-bold px-2 py-0.5 rounded-full {opt.badgeClass}">
									<span
										class="w-1.5 h-1.5 rounded-full {opt.dotColor} {opt.id === 'live' ? 'anim-live' : ''}"
									></span>
									AKTIF
								</span>
							{/if}
						</div>
						<p class="text-xs text-[color:var(--text-muted)] mb-3">{opt.desc}</p>
						<ul class="space-y-1">
							{#each opt.details as d (d)}
								<li class="flex items-start gap-2 text-[11px] text-[color:var(--text-faint)]">
									<svg
										class="w-3 h-3 mt-0.5 shrink-0 {currentModeId === opt.id
											? opt.color
											: 'text-[color:var(--text-faint)]'}"
										fill="none"
										stroke="currentColor"
										viewBox="0 0 24 24"
										stroke-width="2.5"
										><path stroke-linecap="round" stroke-linejoin="round" d="m4.5 12.75 6 6 9-13.5" /></svg
									>
									<span>{d}</span>
								</li>
							{/each}
						</ul>
						{#if switching && switchingMode === opt.id}
							<div
								class="absolute inset-0 rounded-xl bg-[color:var(--surface)]/60 flex items-center justify-center backdrop-blur-sm"
							>
								<div class="flex items-center gap-2.5 font-semibold text-sm">
									<svg class="w-5 h-5 animate-spin" fill="none" viewBox="0 0 24 24"
										><circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4" /><path
											class="opacity-75"
											fill="currentColor"
											d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"
										/></svg
									>
									<span
										>{opt.id === 'live' ? 'Menghubungi 192.168.101.3...' : 'Mengaktifkan simulator...'}</span
									>
								</div>
							</div>
						{/if}
					</button>
				{/each}
			</div>

			<!-- ── SUB-MODE (analisa) ── -->
			{#if showSubModes && currentModeId === 'live'}
				<div class="border-t border-[color:var(--border)] px-4 py-3">
					<div class="flex items-center gap-2 mb-3">
						<svg class="w-3.5 h-3.5 text-[color:var(--text-muted)]" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2"
							><path stroke-linecap="round" stroke-linejoin="round" d="m19.5 8.25-7.5 7.5-7.5-7.5" /></svg
						>
						<span class="text-[11px] font-semibold uppercase tracking-wider text-[color:var(--text-muted)]"
							>Mode Analisa Kerusakan</span
						>
					</div>
					<div class="flex flex-wrap gap-2">
						{#each subModeOptions as sm (sm.id)}
							<button
								class="flex items-center gap-2 px-3 py-2 rounded-lg text-xs font-semibold border transition-all {subModeClass(
									sm,
									pratyaksa.sourceMode === sm.id
								)}"
								onclick={() => setSubMode(sm.id)}
								title={sm.desc}
							>
								<span class="shrink-0">{@html sm.icon}</span>
								<span>{sm.label}</span>
								{#if pratyaksa.sourceMode === sm.id}
									<span class="w-1.5 h-1.5 rounded-full {sm.dotColor}"></span>
								{/if}
							</button>
						{/each}
						<button
							class="flex items-center gap-2 px-3 py-2 rounded-lg text-xs font-semibold border border-[color:var(--border)] text-[color:var(--text-muted)] hover:bg-[color:var(--surface-2)] transition-all"
							onclick={() => ontesttelegram?.()}
						>
							<svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2"
								><path stroke-linecap="round" stroke-linejoin="round" d="M8.29 6.293a9 9 0 1111.418 11.418M12 2a10 10 0 019.95 9M2 12h2m2-6-2-2m14 14l2 2M12 20v2m-4-2l-2 2" /></svg
							>
							Test Telegram
						</button>
					</div>
				</div>
			{/if}

			<!-- ── Connection status ── -->
			{#if currentModeId === 'live'}
				<div
					class="border-t border-[color:var(--border)] px-4 py-2.5 flex items-center gap-3 flex-wrap text-[11px]"
				>
					<div class="flex items-center gap-1.5">
						<span
							class="w-2 h-2 rounded-full {statusInfo.reachable ? 'bg-healthy anim-live' : 'bg-critical'}"
						></span>
						<span class="font-medium {statusInfo.reachable ? 'text-healthy' : 'text-critical'}"
							>{statusInfo.reachable ? 'Terhubung' : 'Tidak Terhubung'}</span
						>
						<span class="text-[color:var(--text-faint)]">ke 192.168.101.3:6000</span>
					</div>
					{#if !isLocked}
						<span class="text-[color:var(--text-faint)]">· Mode auto — akan live jika API reachable</span>
					{:else}
						<span class="text-amber">· Mode manual — terkunci oleh pengguna</span>
					{/if}
				</div>
			{:else}
				<div class="border-t border-[color:var(--border)] px-4 py-2.5 flex items-center gap-1.5 text-[11px] text-[color:var(--text-faint)]">
					<svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2"
						><path stroke-linecap="round" stroke-linejoin="round" d="M9.75 3.104v5.714a2.25 2.25 0 0 1-.659 1.591L5 14.5M9.75 3.104c-.251.023-.501.05-.75.082m.75-.082a24.301 24.301 0 0 1 4.5 0m0 0v5.714c0 .597.237 1.17.659 1.591L19.8 15.3M14.25 3.104c.251.023.501.05.75.082M19.8 15.3l-1.57.393A9.065 9.065 0 0 1 12 15a9.065 9.065 0 0 0-6.23.693L5 14.5m14.8.8 1.402 1.402c1.232 1.232.65 3.318-1.067 3.611A48.309 48.309 0 0 1 12 21c-2.773 0-5.491-.235-8.135-.687-1.718-.293-2.3-2.379-1.067-3.61L5 14.5" /></svg
					>
				<span>Mode simulasi lokal — semua data dari engine Python internal, tidak ada koneksi eksternal</span>
			</div>
		{/if}
	</div>

	<!-- ── COMPACT VERSION ── -->
	{#if compact}
		<div class="flex items-center gap-3 flex-wrap mb-5">
			<div class="flex rounded-xl overflow-hidden border border-[color:var(--border)]">
				{#each modeOptions as opt (opt.id)}
					<button
						class="flex items-center gap-2 px-4 py-2 text-xs font-semibold transition-all {currentModeId === opt.id
							? `${opt.bgColor} ${opt.color}`
							: 'text-[color:var(--text-muted)] hover:bg-[color:var(--surface-2)]'}"
						onclick={() => selectMode(opt.id)}
					>
						<span
							class="w-2 h-2 rounded-full {currentModeId === opt.id
								? opt.dotColor + (opt.id === 'live' ? ' anim-live' : '')
								: 'bg-[color:var(--text-faint)]'}"
						></span>
						{opt.label}
					</button>
				{/each}
			</div>
			{#if isLocked}
				<span
					class="text-[10px] font-semibold px-2 py-0.5 rounded-full bg-amber/15 text-amber border border-amber/30 flex items-center gap-1"
				>
					<svg class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2.5"
						><path stroke-linecap="round" stroke-linejoin="round" d="M16.5 10.5V6.75a4.5 4.5 0 1 0-9 0v3.75m-.75 11.25h10.5a2.25 2.25 0 0 0 2.25-2.25v-6.75a2.25 2.25 0 0 0-2.25-2.25H6.75a2.25 2.25 0 0 0-2.25 2.25v6.75a2.25 2.25 0 0 0 2.25 2.25Z" /></svg
					>
					TERKUNCI
				</span>
			{/if}
			{#if currentModeId === 'live'}
				<span class="text-[10px] flex items-center gap-1.5">
					<span class="w-1.5 h-1.5 rounded-full {statusInfo.reachable ? 'bg-healthy anim-live' : 'bg-critical'}"
					></span>
					<span class={statusInfo.reachable ? 'text-healthy' : 'text-critical'}
						>{statusInfo.reachable ? 'Online' : 'Offline'}</span
					>
				</span>
			{/if}
		</div>
	{/if}
</div>
