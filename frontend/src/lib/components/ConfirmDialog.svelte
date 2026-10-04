<script lang="ts">
	import { confirmDialog } from '$lib/stores/confirm.svelte';

	function onKeydown(e: KeyboardEvent) {
		if (!confirmDialog.open) return;
		if (e.key === 'Escape') confirmDialog.respond(false);
		else if (e.key === 'Enter') confirmDialog.respond(true);
	}
</script>

<svelte:window onkeydown={onKeydown} />

{#if confirmDialog.open}
	<div class="fixed inset-0 z-[210] flex items-center justify-center p-4" role="presentation">
		<div class="modal-backdrop" onclick={() => confirmDialog.respond(false)} role="presentation"></div>
		<div class="modal-card w-full max-w-md p-6 anim-pop" role="alertdialog" aria-modal="true">
			<div class="flex items-start gap-4">
				<div
					class="w-11 h-11 shrink-0 rounded-xl flex items-center justify-center {confirmDialog.opts.danger
						? 'bg-critical/15 text-critical'
						: 'bg-amber/15 text-amber'}"
				>
					<svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2"
						><path stroke-linecap="round" stroke-linejoin="round" d="M12 9v3.75m-9.303 3.376c-.866 1.5.217 3.374 1.948 3.374h14.71c1.73 0 2.813-1.874 1.948-3.374L13.949 3.378c-.866-1.5-3.032-1.5-3.898 0L2.697 16.126ZM12 15.75h.007v.008H12v-.008Z" /></svg
					>
				</div>
				<div class="flex-1 min-w-0">
					<h3 class="font-display text-xl font-bold uppercase tracking-wide">
						{confirmDialog.opts.title || 'Konfirmasi'}
					</h3>
					<p class="text-[color:var(--text-muted)] mt-1.5 break-words">{confirmDialog.opts.message}</p>
				</div>
			</div>
			<div class="flex justify-end gap-3 mt-6">
				<button class="btn btn-ghost px-5" onclick={() => confirmDialog.respond(false)}>
					{confirmDialog.opts.cancelLabel || 'Batal'}
				</button>
				<button
					class="btn px-5 {confirmDialog.opts.danger ? 'btn-danger' : 'btn-amber'}"
					onclick={() => confirmDialog.respond(true)}
				>
					{confirmDialog.opts.confirmLabel || 'Ya'}
				</button>
			</div>
		</div>
	</div>
{/if}
