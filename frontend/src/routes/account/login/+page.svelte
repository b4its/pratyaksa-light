<script lang="ts">
	import { onMount } from 'svelte';
	import { goto } from '$app/navigation';
	import AppLogo from '$lib/components/AppLogo.svelte';
	import { auth } from '$lib/stores/auth.svelte';

	let email = $state('');
	let password = $state('');
	let isLoading = $state(false);
	let showPassword = $state(false);
	let errorMessage = $state('');
	let showResetHint = $state(false);

	onMount(() => auth.init());

	async function handleLogin(e: Event) {
		e.preventDefault();
		isLoading = true;
		errorMessage = '';
		try {
			await auth.login(email, password);
			await goto('/panel/dashboard');
		} catch (error: any) {
			errorMessage = error?.message || 'Login gagal. Periksa email dan password kamu.';
		} finally {
			isLoading = false;
		}
	}
</script>

<div class="min-h-screen bg-topo relative flex items-center justify-center p-4 overflow-hidden text-[color:var(--text)]">
	<div class="absolute inset-0 z-0 pointer-events-none overflow-hidden">
		<div class="absolute -top-32 -left-24 w-96 h-96 rounded-full bg-amber/20 blur-3xl"></div>
		<div class="absolute -bottom-40 -right-24 w-[28rem] h-[28rem] rounded-full bg-steel/20 blur-3xl"></div>
		<div class="absolute inset-0 bg-mesh opacity-60"></div>
	</div>

	<main class="relative z-10 w-full max-w-md panel-raised overflow-hidden anim-pop">
		<div class="h-1.5 hazard-stripe opacity-90"></div>
		<div class="p-8">
			<header class="mb-8">
				<div class="mb-6">
					<AppLogo height="2.75rem" />
					<p class="text-[11px] font-semibold uppercase tracking-[0.2em] text-[color:var(--text-faint)] mt-2">Mining Intelligence</p>
				</div>
				<h1 class="font-display text-4xl font-bold uppercase tracking-wide">Masuk</h1>
				<p class="text-[color:var(--text-muted)] text-sm mt-1">Akses panel kontrol & monitoring armada.</p>
			</header>

			<form onsubmit={handleLogin} class="space-y-5">
				<div>
					<label for="email" class="label">Email Akses</label>
					<input id="email" bind:value={email} type="email" placeholder="engineer@pratyaksa.id" class="field" required />
				</div>

				<div>
					<div class="flex justify-between items-center mb-1">
						<label for="password" class="label !mb-0">Kata Sandi</label>
						<button
							type="button"
							class="text-xs font-semibold text-steel hover:text-amber transition-colors"
							onclick={() => (showResetHint = !showResetHint)}
						>Lupa sandi?</button>
					</div>
					<div class="relative">
						<input
							id="password"
							bind:value={password}
							type={showPassword ? 'text' : 'password'}
							placeholder="••••••••"
							class="field"
							style="padding-right:3rem;"
							required
						/>
						<button
							type="button"
							onclick={() => (showPassword = !showPassword)}
							class="absolute right-2 top-1/2 -translate-y-1/2 p-2 rounded-lg text-[color:var(--text-muted)] hover:text-amber transition-colors"
							aria-label="Toggle password visibility"
						>
							{#if !showPassword}
								<svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M2 12s3-7 10-7 10 7 10 7-3 7-10 7-10-7-10-7Z" /><circle cx="12" cy="12" r="3" /></svg>
							{:else}
								<svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M9.88 9.88a3 3 0 1 0 4.24 4.24" /><path d="M10.73 5.08A10.43 10.43 0 0 1 12 5c7 0 10 7 10 7a13.16 13.16 0 0 1-1.67 2.68" /><path d="M6.61 6.61A13.526 13.526 0 0 0 2 12s3 7 10 7a9.74 9.74 0 0 0 5.39-1.61" /><line x1="2" x2="22" y1="2" y2="22" /></svg>
							{/if}
						</button>
					</div>
				</div>

				{#if showResetHint}
					<div class="flex items-center gap-2 px-4 py-3 rounded-lg bg-steel/10 border border-steel/40 text-[color:var(--text-muted)]">
						<svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><circle cx="12" cy="12" r="10" /><path d="M12 16v-4M12 8h.01" /></svg>
						<span class="font-semibold text-sm">Hubungi administrator untuk reset kata sandi.</span>
					</div>
				{/if}

				{#if errorMessage}
					<div class="flex items-center gap-2 px-4 py-3 rounded-lg bg-critical/10 border border-critical/40 text-critical">
						<svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><path d="m21.73 18-8-14a2 2 0 0 0-3.48 0l-8 14A2 2 0 0 0 4 21h16a2 2 0 0 0 1.73-3Z" /><line x1="12" y1="9" x2="12" y2="13" /><line x1="12" y1="17" x2="12.01" y2="17" /></svg>
						<span class="font-semibold text-sm">{errorMessage}</span>
					</div>
				{/if}

				<button type="submit" disabled={isLoading} class="btn btn-amber w-full !py-3.5 text-base disabled:opacity-70 justify-center gap-2">
					{#if isLoading}
						<span>Memproses…</span>
						<svg class="animate-spin h-5 w-5" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24"><circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle><path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"></path></svg>
					{:else}
						<span>Masuk ke Sistem</span>
						<svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><path d="M5 12h14" /><path d="m12 5 7 7-7 7" /></svg>
					{/if}
				</button>
			</form>

			<div class="mt-8 pt-6 border-t border-[color:var(--border)] text-center space-y-3">
				<p class="text-sm text-[color:var(--text-muted)]">
					Belum punya akses?
					<a href="/account/register" class="font-semibold text-amber hover:underline underline-offset-4 ml-1">Daftar sekarang</a>
				</p>
				<a href="/" class="inline-flex items-center gap-1.5 text-xs font-semibold text-[color:var(--text-faint)] hover:text-steel transition-colors">← Kembali ke Landing Page</a>
			</div>

			<div class="mt-4 text-center text-[11px] text-[color:var(--text-faint)]">
				Demo: admin@pratyaksa.id / admin123
			</div>
		</div>
	</main>
</div>
