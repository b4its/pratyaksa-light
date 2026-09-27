<script lang="ts">
	import { onMount } from 'svelte';
	import { goto } from '$app/navigation';
	import AppLogo from '$lib/components/AppLogo.svelte';
	import { auth } from '$lib/stores/auth.svelte';

	let name = $state('');
	let email = $state('');
	let password = $state('');
	let confirmPassword = $state('');
	let isLoading = $state(false);
	let showPassword = $state(false);
	let showConfirm = $state(false);
	let errorMessage = $state('');

	const passwordMismatch = $derived(confirmPassword.length > 0 && password !== confirmPassword);

	onMount(() => auth.init());

	async function handleRegister(e: Event) {
		e.preventDefault();
		if (passwordMismatch) return;
		isLoading = true;
		errorMessage = '';
		try {
			await auth.register(name, email, password);
			await goto('/panel/dashboard');
		} catch (error: any) {
			errorMessage = error?.message || 'Pendaftaran gagal.';
		} finally {
			isLoading = false;
		}
	}
</script>

<div class="min-h-screen bg-topo relative flex items-center justify-center p-4 py-12 overflow-hidden text-[color:var(--text)]">
	<div class="absolute inset-0 z-0 pointer-events-none overflow-hidden">
		<div class="absolute -top-32 -right-24 w-[28rem] h-[28rem] rounded-full bg-steel/20 blur-3xl"></div>
		<div class="absolute -bottom-40 -left-24 w-96 h-96 rounded-full bg-copper/20 blur-3xl"></div>
		<div class="absolute inset-0 bg-mesh opacity-60"></div>
	</div>

	<main class="relative z-10 w-full max-w-lg panel-raised overflow-hidden anim-pop">
		<div class="h-1.5 hazard-stripe opacity-90"></div>
		<div class="p-8">
			<header class="mb-8 flex justify-between items-start gap-4">
				<div>
					<div class="mb-5">
						<AppLogo height="2.75rem" />
						<p class="text-[11px] font-semibold uppercase tracking-[0.2em] text-[color:var(--text-faint)] mt-2">Mining Intelligence</p>
					</div>
					<h1 class="font-display text-4xl font-bold uppercase tracking-wide">Daftar</h1>
					<p class="text-[color:var(--text-muted)] text-sm mt-1">Buat akun baru untuk mengakses sistem.</p>
				</div>
				<span class="badge bg-amber/15 border-amber/40 text-amber-deep hidden sm:inline-flex">Akses Baru</span>
			</header>

			<form onsubmit={handleRegister} class="space-y-5">
				<div>
					<label for="name" class="label">Nama Lengkap</label>
					<input id="name" bind:value={name} type="text" placeholder="John Doe" class="field" required />
				</div>

				<div>
					<label for="email" class="label">Email</label>
					<input id="email" bind:value={email} type="email" placeholder="engineer@pratyaksa.id" class="field" required />
				</div>

				<div class="grid grid-cols-1 sm:grid-cols-2 gap-5">
					<div>
						<label for="password" class="label">Kata Sandi</label>
						<div class="relative">
							<input id="password" bind:value={password} type={showPassword ? 'text' : 'password'} placeholder="••••••••" class="field" style="padding-right:3rem;" required />
							<button type="button" onclick={() => (showPassword = !showPassword)} class="absolute right-2 top-1/2 -translate-y-1/2 p-2 text-[color:var(--text-muted)] hover:text-amber" aria-label="Toggle">
								<svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M2 12s3-7 10-7 10 7 10 7-3 7-10 7-10-7-10-7Z" /><circle cx="12" cy="12" r="3" /></svg>
							</button>
						</div>
					</div>
					<div>
						<label for="confirmPassword" class="label">Konfirmasi</label>
						<div class="relative">
							<input id="confirmPassword" bind:value={confirmPassword} type={showConfirm ? 'text' : 'password'} placeholder="••••••••" class="field" style="padding-right:3rem;" required />
							<button type="button" onclick={() => (showConfirm = !showConfirm)} class="absolute right-2 top-1/2 -translate-y-1/2 p-2 text-[color:var(--text-muted)] hover:text-amber" aria-label="Toggle">
								<svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M2 12s3-7 10-7 10 7 10 7-3 7-10 7-10-7-10-7Z" /><circle cx="12" cy="12" r="3" /></svg>
							</button>
						</div>
					</div>
				</div>

				{#if passwordMismatch}
					<div class="px-4 py-2.5 rounded-lg bg-critical/10 border border-critical/40 text-critical">
						<span class="font-semibold text-xs uppercase tracking-wide">Kata sandi tidak cocok</span>
					</div>
				{/if}

				{#if errorMessage}
					<div class="px-4 py-3 rounded-lg bg-critical/10 border border-critical/40 text-critical">
						<span class="font-semibold text-sm">{errorMessage}</span>
					</div>
				{/if}

				<button type="submit" disabled={isLoading || passwordMismatch} class="btn btn-amber w-full !py-3.5 text-base disabled:opacity-50">
					{isLoading ? 'Mendaftarkan…' : 'Buat Akun'}
				</button>
			</form>

			<div class="mt-8 pt-6 border-t border-[color:var(--border)] text-center space-y-3">
				<p class="text-sm text-[color:var(--text-muted)]">
					Sudah punya akses?
					<a href="/account/login" class="font-semibold text-amber hover:underline underline-offset-4 ml-1">Masuk</a>
				</p>
				<a href="/" class="inline-flex items-center gap-1.5 text-xs font-semibold text-[color:var(--text-faint)] hover:text-steel transition-colors">← Kembali ke Landing Page</a>
			</div>
		</div>
	</main>
</div>
