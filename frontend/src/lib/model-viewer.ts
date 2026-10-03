/**
 * Loads the `<model-viewer>` web component once per page.
 *
 * The 3D viewers are used across several routes (landing, dashboard,
 * unit_tambang, analisa). Injecting the library in each page is error-prone —
 * a page that forgets the script renders an empty 3D box. Instead the root
 * layout calls `ensureModelViewer()` on mount, so every page gets the custom
 * element registered.
 */

const SCRIPT_SRC =
	'https://ajax.googleapis.com/ajax/libs/model-viewer/3.3.0/model-viewer.min.js';

let loader: Promise<void> | null = null;

/** Inject the model-viewer module script exactly once, resolving when ready. */
export function ensureModelViewer(): Promise<void> {
	if (typeof document === 'undefined') return Promise.resolve();
	if (customElements.get('model-viewer')) return Promise.resolve();
	if (loader) return loader;

	loader = new Promise<void>((resolve) => {
		// Already injected (e.g. by a previous navigation) — just wait for upgrade.
		const existing = document.querySelector<HTMLScriptElement>('script[data-model-viewer]');
		if (existing) {
			customElements.whenDefined('model-viewer').then(() => resolve());
			return;
		}
		const s = document.createElement('script');
		s.type = 'module';
		s.dataset.modelViewer = 'true';
		s.src = SCRIPT_SRC;
		s.onload = () => customElements.whenDefined('model-viewer').then(() => resolve());
		s.onerror = () => resolve(); // don't hang forever on network failure
		document.head.appendChild(s);
	});

	return loader;
}
