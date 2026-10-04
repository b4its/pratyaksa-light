<script lang="ts">
	let { height = '2.25rem', onDark = false } = $props();
</script>

<span
	class="pratyaksa-logo-wrap"
	class:force-on-dark={onDark}
	style="height:{height}"
	role="img"
	aria-label="PRATYAKSA"
>
	<img src="/assets/pratyaksa_logo.png" alt="" class="pratyaksa-logo logo-light" style="height:{height}" draggable="false" />
	<img src="/assets/pratyaksa_logo_dark.png" alt="" class="pratyaksa-logo logo-dark" style="height:{height}" draggable="false" />
</span>

<style>
	.pratyaksa-logo-wrap {
		display: inline-flex;
		align-items: center;
	}
	.pratyaksa-logo {
		width: auto;
		object-fit: contain;
		display: block;
		user-select: none;
	}
	.pratyaksa-logo.logo-dark {
		display: none;
	}
	:global(html.dark) .pratyaksa-logo.logo-light {
		display: none;
	}
	:global(html.dark) .pratyaksa-logo.logo-dark {
		display: block;
	}
	.pratyaksa-logo-wrap.force-on-dark .logo-light {
		display: none;
	}
	.pratyaksa-logo-wrap.force-on-dark .logo-dark {
		display: block;
	}
</style>
