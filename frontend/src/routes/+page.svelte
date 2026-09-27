<script lang="ts">
	import { onMount, onDestroy } from 'svelte';
	import AppLogo from '$lib/components/AppLogo.svelte';
	import { auth } from '$lib/stores/auth.svelte';
	import { theme } from '$lib/stores/theme.svelte';
	import { goto } from '$app/navigation';

	let menuOpen = $state(false);
	let isMounted = $state(false);
	let navOnDark = $state(true);
	let navEl: HTMLElement | null = $state(null);
	let shape1: HTMLElement | null = $state(null);
	let shape2: HTMLElement | null = $state(null);
	let shape3: HTMLElement | null = $state(null);
	let statsSection: HTMLElement | null = $state(null);

	const stats = [
		{ label: 'Physical Availability', target: 93, suffix: '%', accent: '#1FA971' },
		{ label: 'Akurasi AI', target: 95, suffix: '%', accent: '#3E92CC' },
		{ label: 'Reduksi Downtime', target: 45, suffix: '%', accent: '#F2A60C' },
		{ label: 'Hemat Maintenance', target: 30, suffix: '%', accent: '#C2703D' }
	];
	let statDisplay = $state(stats.map(() => 0));
	let statsAnimated = false;

	function animateStats() {
		if (statsAnimated) return;
		statsAnimated = true;
		stats.forEach((s, i) => {
			const start = performance.now();
			const dur = 1400;
			const step = (now: number) => {
				const t = Math.min((now - start) / dur, 1);
				const eased = 1 - Math.pow(1 - t, 3);
				statDisplay[i] = Math.round(s.target * eased);
				if (t < 1) requestAnimationFrame(step);
			};
			requestAnimationFrame(step);
		});
	}

	function updateNavContrast() {
		if (typeof window === 'undefined' || !navEl) return;
		const probeY = navEl.getBoundingClientRect().height / 2;
		const darkEls = [
			document.querySelector('header.hero-bg'),
			document.getElementById('solusi'),
			document.querySelector('footer.section-dark')
		].filter(Boolean) as HTMLElement[];
		let onDark = false;
		for (const el of darkEls) {
			const r = el.getBoundingClientRect();
			if (r.top <= probeY && r.bottom >= probeY) {
				onDark = true;
				break;
			}
		}
		navOnDark = onDark;
	}

	function onMove(e: MouseEvent) {
		const cx = window.innerWidth / 2;
		const cy = window.innerHeight / 2;
		const dx = (e.clientX - cx) / cx;
		const dy = (e.clientY - cy) / cy;
		if (shape1) shape1.style.transform = `translate(${dx * 30}px, ${dy * 30}px)`;
		if (shape2) shape2.style.transform = `translate(${dx * -25}px, ${dy * -25}px)`;
		if (shape3) shape3.style.transform = `translate(${dx * 40}px, ${dy * 40}px)`;
	}

	let statsObs: IntersectionObserver | null = null;
	let contrastTimers: ReturnType<typeof setTimeout>[] = [];

	onMount(() => {
		auth.init();
		theme.init();
		isMounted = true;
		window.addEventListener('mousemove', onMove);
		window.addEventListener('scroll', updateNavContrast, { passive: true });
		window.addEventListener('resize', updateNavContrast);
		updateNavContrast();
		requestAnimationFrame(updateNavContrast);
		contrastTimers.push(setTimeout(updateNavContrast, 300));

		if (statsSection && 'IntersectionObserver' in window) {
			statsObs = new IntersectionObserver(
				(entries) => {
					entries.forEach((en) => {
						if (en.isIntersecting) {
							animateStats();
							statsObs?.disconnect();
						}
					});
				},
				{ threshold: 0.3 }
			);
			statsObs.observe(statsSection);
		} else {
			animateStats();
		}
	});

	onDestroy(() => {
		window.removeEventListener('mousemove', onMove);
		window.removeEventListener('scroll', updateNavContrast);
		window.removeEventListener('resize', updateNavContrast);
		statsObs?.disconnect();
		contrastTimers.forEach((t) => clearTimeout(t));
	});

	function logout() {
		auth.clear();
		goto('/');
	}
</script>

<div class="min-h-screen text-[color:var(--text)] bg-[color:var(--bg)] selection:bg-amber selection:text-graphite-900 font-sans transition-colors duration-500 overflow-x-clip">
	<!-- NAV -->
	<nav
		bind:this={navEl}
		class="{navOnDark ? 'nav-bar--dark' : 'nav-bar--light'} nav-bar sticky top-0 z-50 backdrop-blur-md border-b px-6 py-3.5 flex justify-between items-center w-full transition-colors duration-500"
	>
		<a href="/" class="flex items-center cursor-pointer group">
			<AppLogo height="2.25rem" onDark={navOnDark} />
		</a>

		<div class="hidden xl:flex gap-7 font-semibold items-center text-sm">
			<a href="#tentang" class="hover:text-amber transition-colors">Tentang Kami</a>
			<a href="#solusi" class="hover:text-amber transition-colors">Solusi Pratyaksa</a>
			<a href="#keunggulan" class="hover:text-amber transition-colors">Keunggulan</a>
		</div>

		<div class="flex items-center gap-3">
			<button onclick={() => theme.toggle()} aria-label="Toggle theme" class="btn btn-ghost !p-2.5">
				{#if theme.isDark}
					<svg class="w-5 h-5 text-amber" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 3v1m0 16v1m9-9h-1M4 12H3m15.364 6.364l-.707-.707M6.343 6.343l-.707-.707m12.728 0l-.707.707M6.343 17.657l-.707.707M16 12a4 4 0 11-8 0 4 4 0 018 0z" /></svg>
				{:else}
					<svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M20.354 15.354A9 9 0 018.646 3.646 9.003 9.003 0 0012 21a9.003 9.003 0 008.354-5.646z" /></svg>
				{/if}
			</button>

			{#if auth.isAuthenticated}
				<div class="hidden xl:flex items-center gap-2.5 pl-1 pr-3 py-1.5 rounded-xl border border-[color:var(--border)] bg-[color:var(--surface-2)]">
					<div class="w-8 h-8 rounded-full bg-steel-gradient flex items-center justify-center text-white font-bold text-xs">{(auth.user?.name || 'A').charAt(0).toUpperCase()}</div>
					<span class="font-semibold text-sm truncate text-[color:var(--text)]" style="max-width:120px;">{auth.user?.name || 'Operator'}</span>
				</div>
				<a href="/panel/dashboard" class="btn btn-amber px-6 hidden sm:inline-flex">Buka Dashboard →</a>
				<button onclick={logout} class="btn btn-ghost !p-2.5" title="Keluar" aria-label="Keluar">
					<svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1" /></svg>
				</button>
			{:else}
				<a href="/account/login" class="btn btn-ghost px-6">Masuk</a>
				<a href="/account/register" class="btn btn-amber px-6 hidden sm:inline-flex">Daftar Gratis</a>
			{/if}
			<button onclick={() => (menuOpen = !menuOpen)} class="xl:hidden btn btn-amber !p-2.5" aria-label="Menu">
				<svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2.5" d="M4 6h16M4 12h16M4 18h16" /></svg>
			</button>
		</div>
	</nav>

	{#if menuOpen}
		<div class="xl:hidden fixed inset-0 z-40 bg-[color:var(--surface)] pt-24 px-6 flex flex-col gap-2 font-semibold text-lg">
			<a href="#tentang" onclick={() => (menuOpen = false)} class="py-3 border-b border-[color:var(--border)]">Tentang Kami</a>
			<a href="#solusi" onclick={() => (menuOpen = false)} class="py-3 border-b border-[color:var(--border)]">Solusi Pratyaksa</a>
			<a href="#keunggulan" onclick={() => (menuOpen = false)} class="py-3 border-b border-[color:var(--border)]">Keunggulan</a>
			<div class="mt-6 flex flex-col gap-3">
				{#if auth.isAuthenticated}
					<div class="flex items-center gap-3 p-3 rounded-xl border border-[color:var(--border)] bg-[color:var(--surface-2)]">
						<div class="w-9 h-9 rounded-full bg-steel-gradient flex items-center justify-center text-white font-bold text-sm">{(auth.user?.name || 'A').charAt(0).toUpperCase()}</div>
						<span class="font-semibold truncate">{auth.user?.name || 'Operator'}</span>
					</div>
					<a href="/panel/dashboard" class="btn btn-amber w-full !py-3.5">Buka Dashboard →</a>
					<button onclick={() => { logout(); menuOpen = false; }} class="btn btn-ghost w-full !py-3.5">Keluar</button>
				{:else}
					<a href="/account/login" class="btn btn-ghost w-full !py-3.5">Masuk</a>
					<a href="/account/register" class="btn btn-amber w-full !py-3.5">Daftar Gratis</a>
				{/if}
			</div>
		</div>
	{/if}

	<!-- HERO -->
	<header class="relative overflow-hidden hero-bg text-white transition-colors duration-500">
		<div class="aurora-wrap absolute inset-0 pointer-events-none">
			<span class="aurora aurora-a"></span>
			<span class="aurora aurora-b"></span>
			<span class="aurora aurora-c"></span>
		</div>
		<div class="absolute inset-0 bg-mesh opacity-25"></div>
		<div class="absolute inset-0 bg-topo opacity-20"></div>
		<div bind:this={shape1} class="parallax absolute top-20 left-10 w-24 h-24 rounded-2xl border border-amber/40 bg-amber/10 backdrop-blur-sm hidden md:block anim-float"></div>
		<div bind:this={shape2} class="parallax absolute bottom-28 right-20 w-20 h-20 rounded-full border border-steel/50 bg-steel/10 hidden md:block anim-float" style="animation-delay:1s"></div>
		<div bind:this={shape3} class="parallax absolute top-1/3 right-1/3 w-14 h-14 rounded-xl border border-white/15 bg-white/5 hidden lg:block anim-float" style="animation-delay:.5s"></div>
		<div class="relative z-10 max-w-7xl mx-auto px-6 py-20 md:py-28 grid lg:grid-cols-2 gap-12 items-center">
			<div class="anim-left">
				<div class="inline-flex items-center gap-2 bg-amber/15 text-amber border border-amber/40 px-4 py-1.5 rounded-full font-semibold uppercase text-xs tracking-wider mb-6">
					<span class="w-2 h-2 rounded-full bg-amber anim-live"></span> Mining Intelligence Platform
				</div>
				<h1 class="font-display text-5xl md:text-7xl font-bold uppercase leading-[1.02] tracking-wide mb-6">
					Kendalikan<br />Tambang Anda<br />
					<span class="text-gradient-amber">Dengan Data</span>
				</h1>
				<p class="text-lg md:text-xl mb-8 max-w-xl text-graphite-100 leading-relaxed">
					Pratyaksa mengintegrasikan IoT dan Machine Learning untuk memprediksi kerusakan alat berat dan mengotomatisasi keputusan operasional secara real-time.
				</p>
				<div class="flex flex-col sm:flex-row gap-4">
					{#if auth.isAuthenticated}
						<a href="/panel/dashboard" class="btn btn-amber !py-4 px-8 text-base">Buka Dashboard →</a>
					{:else}
						<a href="/account/register" class="btn btn-amber !py-4 px-8 text-base">Mulai Sekarang →</a>
					{/if}
					<a href="#solusi" class="btn !py-4 px-8 text-base bg-white/10 text-white border border-white/20 hover:bg-white/15 backdrop-blur-sm">Lihat Solusi</a>
				</div>
			</div>

			<div class="anim-pop">
				<div class="viewer-3d rounded-2xl border border-white/10 bg-graphite-950/40 backdrop-blur-sm shadow-elev-lg relative overflow-hidden h-[340px] md:h-[460px] cursor-grab active:cursor-grabbing">
					{#if isMounted}
						<model-viewer
							src="/media/models/dump_truck.glb"
							alt="Visual 3D armada Pratyaksa"
							camera-controls
							auto-rotate
							auto-rotate-delay="0"
							rotation-per-second="32deg"
							shadow-intensity="1.5"
							exposure="1.15"
							environment-image="neutral"
							interaction-prompt="none"
							style="width:100%;height:100%;background-color:transparent;outline:none;"
						></model-viewer>
					{/if}
					<div class="absolute top-3 left-3 bg-steel/90 text-white text-[10px] font-semibold px-2.5 py-1 rounded-full pointer-events-none flex items-center gap-1.5">
						<span class="w-1.5 h-1.5 rounded-full bg-white anim-live"></span> LIVE 3D VISUAL
					</div>
					<div class="absolute bottom-3 right-3 bg-graphite-900/80 text-graphite-100 text-[10px] font-medium px-2.5 py-1 rounded-full pointer-events-none">DRAG UNTUK PUTAR 360°</div>
				</div>
			</div>
		</div>
	</header>

	<!-- MARQUEE -->
	<div class="bg-amber-gradient text-graphite-900 overflow-hidden flex whitespace-nowrap py-2.5 border-y border-amber-deep/30">
		<div class="animate-marquee font-semibold text-sm uppercase tracking-[0.15em] flex gap-6 items-center">
			<span>⚡ IoT Sensor Integration</span><span class="opacity-50">•</span>
			<span>🚧 Predictive Maintenance</span><span class="opacity-50">•</span>
			<span>📊 Machine Learning Analysis</span><span class="opacity-50">•</span>
			<span>⚙️ Automated Alerting</span><span class="opacity-50">•</span>
			<span>⚡ IoT Sensor Integration</span><span class="opacity-50">•</span>
			<span>🚧 Predictive Maintenance</span><span class="opacity-50">•</span>
			<span>📊 Machine Learning Analysis</span><span class="opacity-50">•</span>
			<span>⚙️ Automated Alerting</span>
		</div>
	</div>

	<!-- STATS -->
	<section bind:this={statsSection} class="py-16 px-6 md:px-20 bg-[color:var(--bg)] bg-ore-dots">
		<div class="max-w-6xl mx-auto grid grid-cols-2 lg:grid-cols-4 gap-6">
			{#each stats as s, i (s.label)}
				<div class="kpi p-6 text-center" style="--accent:{s.accent}">
					<p class="font-display text-4xl md:text-5xl font-bold" style="color:{s.accent}">{statDisplay[i]}{s.suffix}</p>
					<p class="text-xs font-semibold uppercase tracking-wider mt-2 text-[color:var(--text-muted)]">{s.label}</p>
				</div>
			{/each}
		</div>
	</section>

	<!-- TENTANG -->
	<section id="tentang" class="py-24 px-6 md:px-20 bg-[color:var(--surface)] relative border-y border-[color:var(--border)]">
		<div class="absolute inset-0 bg-mesh opacity-40"></div>
		<div class="max-w-4xl mx-auto text-center relative z-10 panel-raised p-10">
			<span class="badge bg-copper/10 border-copper/40 text-copper mb-6">Tentang Kami</span>
			<h2 class="font-display text-4xl md:text-6xl font-bold uppercase mb-6 tracking-wide">Apa itu <span class="text-amber">Pratyaksa?</span></h2>
			<div class="w-16 h-1 bg-amber mx-auto mb-8 rounded-full"></div>
			<p class="text-xl md:text-2xl leading-relaxed text-[color:var(--text-muted)]">
				Pratyaksa adalah jembatan antara operasi alat berat dan kecerdasan buatan. Kami mengubah data mentah dari armada tambang menjadi
				<span class="text-amber font-semibold">wawasan preskriptif</span>, memastikan alat berat Anda beroperasi pada efisiensi maksimal.
			</p>
		</div>
	</section>

	<!-- SOLUSI -->
	<section id="solusi" class="py-24 px-6 md:px-20 section-dark text-white relative overflow-hidden">
		<span class="aurora aurora-soft"></span>
		<div class="absolute inset-0 bg-topo opacity-20"></div>
		<div class="max-w-7xl mx-auto relative z-10">
			<span class="badge bg-amber/15 border-amber/40 text-amber mb-5">End-to-End</span>
			<h2 class="font-display text-5xl md:text-6xl font-bold uppercase mb-14 tracking-wide">Solusi End-to-End</h2>
			<div class="grid grid-cols-1 md:grid-cols-3 gap-7">
				<div class="relative overflow-hidden rounded-2xl border border-white/10 bg-white/[0.04] backdrop-blur-sm p-8 flex flex-col h-full hover:border-amber/40 transition-colors">
					<div class="w-14 h-14 rounded-xl bg-amber-gradient flex items-center justify-center mb-6 anim-float">
						<svg class="w-7 h-7 text-graphite-900" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2.2" d="M13 10V3L4 14h7v7l9-11h-7z" /></svg>
					</div>
					<h3 class="font-display text-2xl font-bold uppercase mb-3 tracking-wide">Predictive Maintenance</h3>
					<p class="text-graphite-200 leading-relaxed flex-grow">Mendeteksi anomali suhu, tekanan, dan vibrasi sebelum kerusakan fatal terjadi via Machine Learning.</p>
				</div>
				<div class="relative overflow-hidden rounded-2xl border border-white/10 bg-white/[0.04] backdrop-blur-sm p-8 flex flex-col h-full hover:border-steel/50 transition-colors">
					<div class="w-14 h-14 rounded-xl bg-copper-gradient flex items-center justify-center mb-6 anim-float">
						<svg class="w-7 h-7 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2.2" d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" /></svg>
					</div>
					<h3 class="font-display text-2xl font-bold uppercase mb-3 tracking-wide">Real-time Telematics</h3>
					<p class="text-graphite-200 leading-relaxed flex-grow">Pemantauan lokasi presisi, konsumsi bahan bakar, dan perilaku operator dalam satu dashboard.</p>
				</div>
				<div class="relative overflow-hidden rounded-2xl border border-white/10 bg-white/[0.04] backdrop-blur-sm p-8 flex flex-col h-full hover:border-steel/50 transition-colors">
					<div class="w-14 h-14 rounded-xl bg-steel flex items-center justify-center mb-6 anim-float">
						<svg class="w-7 h-7 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2.2" d="M8 10h.01M12 10h.01M16 10h.01M9 16H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-5l-5 5v-5z" /></svg>
					</div>
					<h3 class="font-display text-2xl font-bold uppercase mb-3 tracking-wide">Automated Alerting</h3>
					<p class="text-graphite-200 leading-relaxed flex-grow">Sistem preskriptif otomatis yang merilis tiket perbaikan via Telegram & WhatsApp ke tim mekanik.</p>
				</div>
			</div>
		</div>
	</section>

	<!-- KEUNGGULAN -->
	<section id="keunggulan" class="py-24 px-6 md:px-20 bg-[color:var(--surface)] border-b border-[color:var(--border)]">
		<div class="max-w-7xl mx-auto flex flex-col lg:flex-row gap-16 items-center">
			<div class="w-full lg:w-1/2">
				<div class="viewer-3d w-full aspect-square rounded-2xl border border-[color:var(--border)] bg-steel-gradient shadow-neo relative overflow-hidden cursor-grab active:cursor-grabbing">
					<div class="absolute top-0 left-0 w-full h-10 border-b border-white/10 bg-graphite-900/60 backdrop-blur flex items-center px-4 gap-2 z-10">
						<div class="w-3 h-3 rounded-full bg-critical"></div>
						<div class="w-3 h-3 rounded-full bg-warning"></div>
						<div class="w-3 h-3 rounded-full bg-healthy"></div>
						<span class="ml-auto text-[10px] font-mono text-graphite-300">pratyaksa://3d-viewer</span>
					</div>
					{#if isMounted}
						<model-viewer
							src="/media/models/bulldozer.glb"
							alt="Showcase 3D"
							camera-controls
							auto-rotate
							auto-rotate-delay="0"
							rotation-per-second="28deg"
							shadow-intensity="1.4"
							exposure="1.1"
							environment-image="neutral"
							interaction-prompt="none"
							style="width:100%;height:100%;background-color:transparent;outline:none;"
						></model-viewer>
					{/if}
				</div>
			</div>
			<div class="w-full lg:w-1/2 space-y-6">
				<span class="badge bg-amber/10 border-amber/40 text-amber-deep">Keunggulan</span>
				<h2 class="font-display text-4xl md:text-5xl font-bold uppercase tracking-wide">Kenapa <span class="text-amber">Pratyaksa?</span></h2>
				<ul class="space-y-6">
					<li class="flex gap-5 group">
						<div class="w-12 h-12 shrink-0 rounded-xl bg-amber/15 border border-amber/40 flex justify-center items-center text-amber group-hover:bg-amber group-hover:text-graphite-900 transition-all">
							<svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2.5" d="M5 13l4 4L19 7" /></svg>
						</div>
						<div>
							<h4 class="font-display text-2xl font-bold mb-1.5 uppercase tracking-wide">Agnostik Terhadap Merek</h4>
							<p class="text-[color:var(--text-muted)] leading-relaxed">Sensor IoT kami terintegrasi dengan berbagai merk (Komatsu, Caterpillar, Volvo) tanpa kendala.</p>
						</div>
					</li>
					<li class="flex gap-5 group">
						<div class="w-12 h-12 shrink-0 rounded-xl bg-steel/15 border border-steel/40 flex justify-center items-center text-steel group-hover:bg-steel group-hover:text-white transition-all">
							<svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2.5" d="M5 13l4 4L19 7" /></svg>
						</div>
						<div>
							<h4 class="font-display text-2xl font-bold mb-1.5 uppercase tracking-wide">Infrastruktur Berbasis Lokal</h4>
							<p class="text-[color:var(--text-muted)] leading-relaxed">Skalabilitas tinggi. Data aman dan dapat diakses dari site tambang mana pun dengan latensi minimal.</p>
						</div>
					</li>
					<li class="flex gap-5 group">
						<div class="w-12 h-12 shrink-0 rounded-xl bg-copper/15 border border-copper/40 flex justify-center items-center text-copper group-hover:bg-copper group-hover:text-white transition-all">
							<svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2.5" d="M5 13l4 4L19 7" /></svg>
						</div>
						<div>
							<h4 class="font-display text-2xl font-bold mb-1.5 uppercase tracking-wide">ROI Terukur Cepat</h4>
							<p class="text-[color:var(--text-muted)] leading-relaxed">Klien mencatatkan penghematan biaya <b>maintenance</b> hingga 25% pada kuartal pertama implementasi.</p>
						</div>
					</li>
				</ul>
				<a href="/account/register" class="btn btn-amber !py-3.5 px-8 inline-flex">Coba Sekarang →</a>
			</div>
		</div>
	</section>

	<!-- FOOTER -->
	<footer class="py-14 px-6 md:px-20 bg-graphite-950 text-graphite-300">
		<div class="max-w-7xl mx-auto flex flex-col md:flex-row justify-between gap-8">
			<div>
				<AppLogo height="2rem" onDark={true} />
				<p class="text-sm mt-3 max-w-sm">Predictive Analytics & Traceability for Heavy Asset Condition Surveillance and Actualization.</p>
			</div>
			<div class="text-sm space-y-2">
				<p class="font-semibold text-white uppercase tracking-wide text-xs">Tim Oryphem</p>
				<p>Politeknik Negeri Samarinda</p>
				<p>Kideco Innovation Challenge 2026</p>
			</div>
		</div>
		<div class="max-w-7xl mx-auto mt-10 pt-6 border-t border-white/10 text-xs text-graphite-500">
			© 2026 PRATYAKSA — Mining Intelligence Platform.
		</div>
	</footer>
</div>

<style>
	.hero-bg {
		background: linear-gradient(160deg, #0c1014 0%, #141a21 45%, #1d242e 100%);
	}
	.section-dark {
		background: linear-gradient(160deg, #141a21 0%, #0c1014 100%);
	}
	.text-gradient-amber {
		background: linear-gradient(135deg, #f2a60c 0%, #d9930a 100%);
		-webkit-background-clip: text;
		background-clip: text;
		-webkit-text-fill-color: transparent;
		color: transparent;
	}
	.bg-amber-gradient {
		background: linear-gradient(135deg, #f2a60c 0%, #d9930a 100%);
	}
	.bg-copper-gradient {
		background: linear-gradient(135deg, #d98049 0%, #b65a2c 100%);
	}
	.bg-steel-gradient {
		background: linear-gradient(135deg, #2c3643 0%, #141a21 100%);
	}
	.animate-marquee {
		animation: marquee 26s linear infinite;
	}
	@keyframes marquee {
		from {
			transform: translateX(0);
		}
		to {
			transform: translateX(-50%);
		}
	}
	.viewer-3d {
		container-type: inline-size;
	}
</style>
