/**
 * Shared Chart.js theme palette.
 *
 * Reading CSS custom properties via `getComputedStyle` is expensive, so the
 * palette is cached and only recomputed when the cache is invalidated (e.g. on
 * theme toggle). Call `invalidateChartTheme()` when the theme changes.
 */

export interface ChartTheme {
	tick: string;
	grid: string;
	axis: string;
	surface: string;
	text: string;
}

let cache: ChartTheme | null = null;

function css(v: string): string {
	if (typeof window === 'undefined') return '';
	return getComputedStyle(document.documentElement).getPropertyValue(v).trim();
}

export function invalidateChartTheme(): void {
	cache = null;
}

export function chartTheme(): ChartTheme {
	if (cache) return cache;
	cache = {
		tick: css('--text-muted') || '#5d6b7a',
		grid: css('--border') || '#d7dde4',
		axis: css('--border-strong') || '#c2cad3',
		surface: css('--surface') || '#ffffff',
		text: css('--text') || '#1b2128'
	};
	return cache;
}
