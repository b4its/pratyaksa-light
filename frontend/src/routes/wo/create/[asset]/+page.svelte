<script lang="ts">
	import { onMount } from 'svelte';
	import { goto } from '$app/navigation';
	import { page } from '$app/state';

	const asset = $derived(page.params.asset || '');

	onMount(() => {
		const query = asset ? `?asset=${asset}` : '';
		goto(`/panel/work_order${query}`, { replaceState: true });
	});
</script>

<div class="flex items-center justify-center h-screen text-[color:var(--text-muted)] font-semibold uppercase tracking-widest">
	Mengarahkan ke Work Order…
</div>
