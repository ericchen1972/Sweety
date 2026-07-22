import type { BasePersona } from "./domain";
import personaData from "./catalog.generated.json";

export const basePersonas: BasePersona[] = personaData.map(({ sortOrder: _sortOrder, ...persona }) => persona) as BasePersona[];
