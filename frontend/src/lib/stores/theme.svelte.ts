/** Theme store — mirrors Nuxt `useTheme` (dark/light, synced to localStorage). */
class ThemeStore {
	isDark = $state(false);

	apply(dark: boolean) {
		this.isDark = dark;
		if (typeof document !== 'undefined') {
			document.documentElement.classList.toggle('dark', dark);
		}
	}

	init() {
		if (typeof localStorage === 'undefined') return;
		const saved = localStorage.getItem('theme');
		const osPrefersDark =
			typeof window !== 'undefined' && window.matchMedia('(prefers-color-scheme: dark)').matches;
		this.apply(saved === 'dark' || (!saved && osPrefersDark));
	}

	toggle() {
		const next = !this.isDark;
		this.apply(next);
		if (typeof localStorage !== 'undefined') localStorage.setItem('theme', next ? 'dark' : 'light');
	}

	set(dark: boolean) {
		this.apply(dark);
		if (typeof localStorage !== 'undefined') localStorage.setItem('theme', dark ? 'dark' : 'light');
	}
}

export const theme = new ThemeStore();
