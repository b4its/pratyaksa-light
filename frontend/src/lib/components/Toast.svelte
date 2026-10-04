<script lang="ts">
	import { toast } from '$lib/stores/toast.svelte';
</script>

{#if toast.state.open}
	<div
		class="fixed z-[200] top-4 right-4 max-w-sm w-[calc(100%-2rem)] sm:w-auto anim-pop"
		role="status"
		aria-live="polite"
	>
		<div
			class="flex items-start gap-3 px-4 py-3 rounded-xl shadow-elev-lg border {toast.state.kind === 'success'
				? 'bg-healthy/15 border-healthy/40 text-healthy'
				: 'bg-critical/15 border-critical/40 text-critical'}"
		>
			{#if toast.state.kind === 'success'}
				<svg class="w-5 h-5 shrink-0 mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2.5"
					><path stroke-linecap="round" stroke-linejoin="round" d="M9 12.75 11.25 15 15 9.75M21 12a9 9 0 1 1-18 0 9 9 0 0 1 18 0Z" /></svg
				>
			{:else}
				<svg class="w-5 h-5 shrink-0 mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2.5"
					><path stroke-linecap="round" stroke-linejoin="round" d="M12 9v3.75m9-.75a9 9 0 1 1-18 0 9 9 0 0 1 18 0Zm-9 3.75h.008v.008H12v-.008Z" /></svg
				>
			{/if}
			<span class="font-semibold text-sm flex-1">{toast.state.message}</span>
			<button class="opacity-70 hover:opacity-100 shrink-0" aria-label="Tutup notifikasi" onclick={() => toast.dismiss()}>✕</button>
		</div>
	</div>
{/if}
