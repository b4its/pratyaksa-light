<script lang="ts">
	import { onMount } from 'svelte';
	import { page } from '$app/state';
	import { goto } from '$app/navigation';
	import AppLogo from './AppLogo.svelte';
	import { auth } from '$lib/stores/auth.svelte';
	import { theme } from '$lib/stores/theme.svelte';

	interface MenuItem {
		name: string;
		path: string;
		icon: string;
	}

	const menuItems: MenuItem[] = [
		{
			name: 'Dashboard',
			path: '/panel/dashboard',
			icon: '<rect width="7" height="9" x="3" y="3" rx="1"/><rect width="7" height="5" x="14" y="3" rx="1"/><rect width="7" height="9" x="14" y="12" rx="1"/><rect width="7" height="5" x="3" y="16" rx="1"/>'
		},
		{
			name: 'Jenis Alat Berat',
			path: '/panel/jenis_alat_berat',
			icon: '<path d="M10 17h4V5H2v12h3"/><path d="M20 17h2v-9l-2.5-3.5H14v12h3"/><path d="M14 6h4.5"/><circle cx="18.5" cy="17.5" r="2.5"/><circle cx="5.5" cy="17.5" r="2.5"/>'
		},
		{
			name: 'Unit Tambang',
			path: '/panel/unit_tambang',
			icon: '<polygon points="12 2 2 7 12 12 22 7 12 2"/><polyline points="2 12 12 17 22 12"/><polyline points="2 17 12 22 22 17"/>'
		},
		{
			name: 'Analisa Kerusakan',
			path: '/panel/analisa',
			icon: '<path d="M14.7 6.3a1 1 0 0 0 0 1.4l1.6 1.6a1 1 0 0 0 1.4 0l3.77-3.77a6 6 0 0 1-7.94 7.94l-6.91 6.91a2.12 2.12 0 0 1-3-3l6.91-6.91a6 6 0 0 1 7.94-7.94l-3.76 3.76z"/>'
		},
		{
			name: 'Work Order',
			path: '/panel/work_order',
			icon: '<path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/><path d="M18.5 2.5a2.12 2.12 0 0 1 3 3L12 15l-4 1 1-4Z"/>'
		},
		{
			name: 'Kembali',
			path: '/',
			icon: '<path d="m12 19-7-7 7-7"/><path d="M19 12H5"/>'
		}
	];

	let collapsed = $state(false);
	let mobileOpen = $state(false);

	onMount(() => {
		if (typeof localStorage !== 'undefined') {
			collapsed = localStorage.getItem('panel_sidebar_collapsed') === '1';
		}
	});

	function toggleCollapse() {
		collapsed = !collapsed;
		if (typeof localStorage !== 'undefined')
			localStorage.setItem('panel_sidebar_collapsed', collapsed ? '1' : '0');
	}

	function isActive(path: string) {
		return path !== '/' && page.url.pathname === path;
	}

	function logout() {
		auth.clear();
		goto('/account/login');
	}
</script>

<!-- Mobile hamburger -->
<button
	class="lg:hidden fixed top-3 left-3 z-[60] w-11 h-11 rounded-xl bg-[color:var(--surface)] border border-[color:var(--border)] shadow-elev-sm flex items-center justify-center text-[color:var(--text)]"
	aria-label="Buka menu"
	onclick={() => (mobileOpen = true)}
>
	<svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2.2"
		><path d="M4 6h16M4 12h16M4 18h16" /></svg
	>
</button>

{#if mobileOpen}
	<div
		class="lg:hidden fixed inset-0 z-[70] bg-black/50 backdrop-blur-sm"
		onclick={() => (mobileOpen = false)}
		role="presentation"
	></div>
{/if}

<aside
	class={[
		'fixed lg:static inset-y-0 left-0 z-[71] lg:z-10 h-screen shrink-0 flex flex-col justify-between',
		'border-r border-[color:var(--border)] bg-[color:var(--surface)] overflow-y-auto overflow-x-hidden',
		'transition-all duration-300 ease-out',
		collapsed ? 'p-3 lg:w-20' : 'p-5 lg:w-72',
		'w-72',
		mobileOpen ? 'translate-x-0' : '-translate-x-full lg:translate-x-0'
	].join(' ')}
>
	<div>
		<div class={['flex items-start justify-between gap-2 mb-8', collapsed ? 'flex-col items-center gap-3' : ''].join(' ')}>
			<div class={collapsed ? 'flex justify-center w-full' : ''}>
				{#if !collapsed}
					<AppLogo height="2.4rem" />
					<p class="text-[10px] font-semibold uppercase tracking-[0.18em] text-[color:var(--text-faint)] mt-2">
						Control Panel
					</p>
				{:else}
					<img src="/assets/pratyaksa_icon.png" alt="PRATYAKSA" class="w-10 h-10 object-contain" />
				{/if}
			</div>
			<button class="lg:hidden p-1.5 rounded-lg hover:bg-[color:var(--surface-2)]" aria-label="Tutup menu" onclick={() => (mobileOpen = false)}>
				<svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2.2"
					><path d="M6 18L18 6M6 6l12 12" /></svg
				>
			</button>
			<button
				class="hidden lg:flex p-1.5 rounded-lg hover:bg-[color:var(--surface-2)] text-[color:var(--text-muted)]"
				aria-label="Ciutkan sidebar"
				onclick={toggleCollapse}
			>
				<svg
					class="w-5 h-5 transition-transform"
					class:rotate-180={collapsed}
					fill="none"
					stroke="currentColor"
					viewBox="0 0 24 24"
					stroke-width="2.2"
					><path d="M15 18l-6-6 6-6" /></svg
				>
			</button>
		</div>

		<nav class="space-y-1.5">
			{#each menuItems as item (item.name)}
				<a
					href={item.path}
					class={['nav-link', isActive(item.path) ? 'nav-link-active' : '', collapsed ? 'lg:justify-center lg:px-0' : ''].join(' ')}
					title={collapsed ? item.name : undefined}
				>
					<span class="flex items-center justify-center shrink-0">
						<svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
							{@html item.icon}
						</svg>
					</span>
					{#if !collapsed}<span class="truncate">{item.name}</span>{/if}
				</a>
			{/each}
		</nav>
	</div>

	<div class="space-y-2 mt-6">
		<button class={['theme-toggle', collapsed ? 'lg:justify-center' : ''].join(' ')} aria-label="Ganti tema" onclick={() => theme.toggle()}>
			<span class="flex items-center gap-2.5 font-semibold text-sm">
				{#if theme.isDark}
					<svg class="w-4 h-4 text-amber" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2"
						><path stroke-linecap="round" stroke-linejoin="round" d="M20.354 15.354A9 9 0 018.646 3.646 9.003 9.003 0 0012 21a9.003 9.003 0 008.354-5.646z" /></svg
					>
				{:else}
					<svg class="w-4 h-4 text-amber" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2"
						><path stroke-linecap="round" stroke-linejoin="round" d="M12 3v1m0 16v1m9-9h-1M4 12H3m15.364 6.364l-.707-.707M6.343 6.343l-.707-.707m12.728 0l-.707.707M6.343 17.657l-.707.707M16 12a4 4 0 11-8 0 4 4 0 018 0z" /></svg
					>
				{/if}
				{#if !collapsed}<span>{theme.isDark ? 'Mode Gelap' : 'Mode Terang'}</span>{/if}
			</span>
			{#if !collapsed}
				<span class="tt-switch" class:tt-on={theme.isDark}><span class="tt-knob"></span></span>
			{/if}
		</button>

		<div class={['panel-flat', collapsed ? 'p-2 flex justify-center' : 'p-4'].join(' ')}>
			{#if !collapsed}
				<p class="text-[10px] font-semibold uppercase tracking-wider text-[color:var(--text-faint)]">Logged in as</p>
				<div class="flex items-center gap-3 mt-2">
					<div class="w-9 h-9 rounded-full bg-steel-gradient flex items-center justify-center text-white font-bold text-sm">
						{(auth.user?.name || 'A').charAt(0).toUpperCase()}
					</div>
					<p class="font-semibold text-sm truncate">{auth.user?.name || 'Admin'}</p>
				</div>
				<button class="mt-3 w-full text-left text-xs font-semibold text-critical hover:underline" onclick={logout}>
					Keluar
				</button>
			{:else}
				<div class="w-9 h-9 rounded-full bg-steel-gradient flex items-center justify-center text-white font-bold text-sm" title={auth.user?.name || 'Admin'}>
					{(auth.user?.name || 'A').charAt(0).toUpperCase()}
				</div>
			{/if}
		</div>
	</div>
</aside>

<style>
	.bg-steel-gradient {
		background: linear-gradient(135deg, #2c3643 0%, #141a21 100%);
	}
</style>
