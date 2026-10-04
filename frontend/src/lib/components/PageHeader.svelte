<script lang="ts">
	/** Consistent page header used across all panel pages. */
	let {
		title,
		subtitle = '',
		lastUpdate = '',
		children
	}: {
		title: string;
		subtitle?: string;
		lastUpdate?: string;
		children?: any;
	} = $props();
</script>

<header class="flex justify-between items-start mb-8 gap-4 flex-wrap">
	<div>
		<h1 class="font-display text-4xl md:text-5xl font-bold uppercase tracking-wide leading-none">{title}</h1>
		{#if subtitle}<p class="mt-2 text-[color:var(--text-muted)]">{subtitle}</p>{/if}
	</div>
	<div class="flex items-center gap-3 flex-wrap">
		{#if children}{@render children()}{/if}
		{#if lastUpdate}
			<div class="panel-flat px-3 py-2 text-[10px] font-mono text-[color:var(--text-muted)]">
				Update<br /><span class="font-semibold text-[color:var(--text)]">{lastUpdate || '—'}</span>
			</div>
		{/if}
	</div>
</header>
