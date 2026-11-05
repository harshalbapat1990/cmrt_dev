/** Stable, case-insensitive, locale-aware ordering for user-facing choices. */
const optionLabelCollator = new Intl.Collator(undefined, {
  sensitivity: 'base',
  numeric: true,
});

export type OptionOrder = 'alphabetical' | 'provided';

export function compareOptionLabels(left: string, right: string): number {
  return optionLabelCollator.compare(left, right);
}

export function sortOptionsByLabel<T extends { label: string }>(options: readonly T[]): T[] {
  return [...options].sort((left, right) => compareOptionLabels(left.label, right.label));
}

export function sortNamedOptions<T extends { name: string }>(options: readonly T[]): T[] {
  return [...options].sort((left, right) => compareOptionLabels(left.name, right.name));
}
