<script lang="ts">
	/**
	 * Shared modal shell.
	 *
	 * Handles the repetitive, easy-to-get-wrong parts consistently:
	 * - `role="dialog"` + `aria-modal` + `aria-labelledby`
	 * - focus trap (Tab/Shift-Tab cycle inside the card)
	 * - autofocus of the first focusable element (or `autofocus` selector)
	 * - focus restore to the previously focused element on close
	 * - Escape-to-close + backdrop click-to-close
	 * - `max-h-[90vh]` with scrollable body
	 */
	import { onMount, tick } from 'svelte';
	import { fade, fly } from 'svelte/transition';

	let {
		open = true,
		title = '',
		onclose,
		maxWidth = 'lg',
		zIndex = 50,
		bodyClass = '',
		closeOnBackdrop = true,
		children
	}: {
		open?: boolean;
		title?: string;
		onclose: () => void;
		maxWidth?: 'sm' | 'md' | 'lg' | 'xl' | '2xl' | '3xl' | '4xl';
		zIndex?: number;
		bodyClass?: string;
		closeOnBackdrop?: boolean;
		children: any;
	} = $props();

	const widthClass: Record<string, string> = {
		sm: 'max-w-sm',
		md: 'max-w-md',
		lg: 'max-w-lg',
		xl: 'max-w-xl',
		'2xl': 'max-w-2xl',
		'3xl': 'max-w-3xl',
		'4xl': 'max-w-4xl'
	};

	let card: HTMLElement | null = $state(null);
	let titleId = `modal-title-${Math.random().toString(36).slice(2, 9)}`;
	let prevFocus: HTMLElement | null = null;

	const FOCUSABLE =
		'a[href], button:not([disabled]), textarea:not([disabled]), input:not([disabled]), select:not([disabled]), [tabindex]:not([tabindex="-1"])';

	function focusables(): HTMLElement[] {
		if (!card) return [];
		return Array.from(card.querySelectorAll<HTMLElement>(FOCUSABLE)).filter(
			(el) => el.offsetParent !== null || el === document.activeElement
		);
	}

	async function focusFirst() {
		await tick();
		const els = focusables();
		// Prefer an element explicitly marked autofocus, else the first field,
		// else the first focusable (usually the close button).
		const preferred =
			card?.querySelector<HTMLElement>('[data-autofocus]') ||
			els.find((el) => ['INPUT', 'TEXTAREA', 'SELECT'].includes(el.tagName)) ||
			els[0];
		(preferred ?? card)?.focus();
	}

	function onKeydown(e: KeyboardEvent) {
		if (!open) return;
		if (e.key === 'Escape') {
			e.stopPropagation();
			onclose();
			return;
		}
		if (e.key === 'Tab') {
			const els = focusables();
			if (els.length === 0) {
				e.preventDefault();
				return;
			}
			const first = els[0];
			const last = els[els.length - 1];
			const active = document.activeElement as HTMLElement | null;
			if (e.shiftKey && (active === first || !card?.contains(active))) {
				e.preventDefault();
				last.focus();
			} else if (!e.shiftKey && active === last) {
				e.preventDefault();
				first.focus();
			}
		}
	}

	$effect(() => {
		if (open) {
			prevFocus = (document.activeElement as HTMLElement) ?? null;
			focusFirst();
		} else if (prevFocus) {
			prevFocus.focus?.();
			prevFocus = null;
		}
	});
</script>

{#if open}
	<div class="fixed inset-0 flex items-center justify-center p-4" style="z-index:{zIndex}" role="presentation">
		<div
			class="modal-backdrop"
			transition:fade={{ duration: 120 }}
			onclick={closeOnBackdrop ? onclose : undefined}
			role="presentation"
		></div>
		<div
			class="modal-card w-full {widthClass[maxWidth] || 'max-w-lg'} flex flex-col max-h-[90vh] outline-none"
			transition:fly={{ y: 14, duration: 220 }}
			role="dialog"
			aria-modal="true"
			aria-labelledby={title ? titleId : undefined}
			tabindex="-1"
			bind:this={card}
			onkeydown={onKeydown}
		>
			<div class="flex justify-between items-center px-6 py-4 border-b border-[color:var(--border)] bg-[color:var(--surface-2)] shrink-0">
				<h3 id={titleId} class="font-display text-2xl font-bold uppercase tracking-wide">{title}</h3>
				<button
					class="w-9 h-9 rounded-lg hover:bg-critical/15 hover:text-critical text-[color:var(--text-muted)] flex items-center justify-center transition-colors"
					aria-label="Tutup"
					onclick={onclose}
				>✕</button>
			</div>
			<div class={['overflow-y-auto', bodyClass].join(' ')}>
				{@render children()}
			</div>
		</div>
	</div>
{/if}
