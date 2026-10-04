/** Simple app-wide toast store (success/error/info notifications). */

export type ToastKind = 'success' | 'error';

interface ToastState {
	open: boolean;
	kind: ToastKind;
	message: string;
}

class ToastStore {
	state = $state<ToastState>({ open: false, kind: 'success', message: '' });
	private timer: ReturnType<typeof setTimeout> | null = null;

	success(message: string, ms = 4000) {
		this.show('success', message, ms);
	}
	error(message: string, ms = 6000) {
		this.show('error', message, ms);
	}

	private show(kind: ToastKind, message: string, ms: number) {
		this.state = { open: true, kind, message };
		if (this.timer) clearTimeout(this.timer);
		this.timer = setTimeout(() => (this.state.open = false), ms);
	}

	dismiss() {
		this.state.open = false;
		if (this.timer) {
			clearTimeout(this.timer);
			this.timer = null;
		}
	}
}

export const toast = new ToastStore();
