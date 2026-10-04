<script lang="ts">
	import { onMount } from 'svelte';
	import { page } from '$app/state';
	import { theme } from '$lib/stores/theme.svelte';
	import { auth } from '$lib/stores/auth.svelte';
	import { ensureModelViewer } from '$lib/model-viewer';
	import { fly, fade } from 'svelte/transition';

	let { children } = $props();

	// Panel routes own their own transition (inside the panel layout) so the
	// sidebar is NOT re-mounted/animated on every panel navigation. Other
	// routes get the page transition here.
	const isPanel = $derived(page.url.pathname.startsWith('/panel'));

	onMount(() => {
		theme.init();
		auth.init();
		// Register the <model-viewer> custom element for every route that
		// renders 3D models (landing, dashboard, unit_tambang, analisa).
		ensureModelViewer();
	});
</script>

<svelte:head>
	<title>Pratyaksa</title>
</svelte:head>

{#if isPanel}
	{@render children()}
{:else}
	{#key page.url.pathname}
		<div in:fly={{ y: 14, duration: 320 }} out:fade={{ duration: 150 }}>
			{@render children()}
		</div>
	{/key}
{/if}
