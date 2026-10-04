/**
 * Promise-based confirm dialog store + component.
 *
 * Usage:
 *   if (await confirmDialog.ask({ title, message })) { ... }
 */

interface ConfirmOptions {
	title?: string;
	message: string;
	confirmLabel?: string;
	cancelLabel?: string;
	danger?: boolean;
	// Kept for compatibility with the legacy error envelope shape.
	error?: string;
}

class ConfirmDialogStore {
	open = $state(false);
	opts = $state<ConfirmOptions>({ message: '' });
	private resolver: ((ok: boolean) => void) | null = null;

	ask(opts: ConfirmOptions): Promise<boolean> {
		// If a dialog is already open, resolve the previous one as cancelled.
		this.resolver?.(false);
		this.opts = { danger: true, confirmLabel: 'Hapus', cancelLabel: 'Batal', ...opts };
		this.open = true;
		return new Promise<boolean>((resolve) => {
			this.resolver = resolve;
		});
	}

	respond(ok: boolean) {
		this.open = false;
		const r = this.resolver;
		this.resolver = null;
		r?.(ok);
	}
}

export const confirmDialog = new ConfirmDialogStore();
