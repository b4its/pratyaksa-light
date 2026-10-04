<script lang="ts">
	import { onMount } from 'svelte';
	import { goto } from '$app/navigation';
	import { page } from '$app/state';
	import { fly, fade } from 'svelte/transition';
	import PanelSidebar from '$lib/components/PanelSidebar.svelte';
	import { auth } from '$lib/stores/auth.svelte';

	let { children } = $props();

	onMount(() => {
		auth.init();
		if (!auth.isAuthenticated) {
			goto('/account/login');
		}
	});
</script>

{#if auth.isAuthenticated}
	<div class="flex min-h-screen bg-topo text-[color:var(--text)]">
		<PanelSidebar />
		<main class="flex-1 min-w-0 p-4 lg:p-8">
			{#key page.url.pathname}
				<div in:fly={{ y: 14, duration: 320 }} out:fade={{ duration: 150 }}>
					{@render children()}
				</div>
			{/key}
		</main>
	</div>
{:else}
	<div class="flex items-center justify-center h-screen text-[color:var(--text-muted)] font-semibold uppercase tracking-widest">
		Memeriksa sesi…
	</div>
{/if}
