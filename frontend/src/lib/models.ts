/** Model 3D resolution — mirrors Nuxt `useModels`. */
const MODELS = {
	excavator: '/media/models/crane.glb',
	haul_truck: '/media/models/dump_truck.glb',
	bulldozer: '/media/models/bulldozer.glb',
	wheel_loader: '/media/models/tractor.glb',
	forklift: '/media/models/forklift.glb',
	default: '/media/models/bulldozer.glb'
} as const;

export function modelForType(nama?: string | null): string {
	const j = (nama || '').toLowerCase();
	if (['haul_truck', 'dump_truck'].includes(j) || j.includes('dump') || j.includes('haul') || j.includes('truck'))
		return MODELS.haul_truck;
	if (j === 'excavator' || j.includes('excav') || j.includes('zaxis') || j.includes('digger') || j.includes('crane'))
		return MODELS.excavator;
	if (j === 'bulldozer' || j.includes('dozer')) return MODELS.bulldozer;
	if (j === 'wheel_loader' || j.includes('loader')) return MODELS.wheel_loader;
	if (j.includes('forklift')) return MODELS.forklift;
	return MODELS.default;
}

export function resolveModel(model3dUrl?: string | null, jenis?: string | null): string {
	return model3dUrl && model3dUrl.trim() ? model3dUrl : modelForType(jenis);
}

export { MODELS };
