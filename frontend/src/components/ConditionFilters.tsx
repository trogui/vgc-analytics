import { useState } from "react";

import { formatPercent } from "../format";
import type { PokemonCondition, PokemonOptions, UsageOption } from "../types";

type ConditionType = "moves" | "item" | "ability";

interface GroupProps {
  title: string;
  type: ConditionType;
  options: UsageOption[];
  selected: string[];
  multiple?: boolean;
  expandable?: boolean;
  onToggle: (value: string, checked: boolean) => void;
  onClear: () => void;
}

function FilterGroup({ title, type, options, selected, multiple = false, expandable = false, onToggle, onClear }: GroupProps) {
  const [expanded, setExpanded] = useState(false);
  const visible = expandable && !expanded ? options.slice(0, 6) : options;
  return (
    <section className="filter-group">
      <div className="filter-group-header"><strong>{title}</strong><button type="button" disabled={!selected.length} onClick={onClear}>Clear</button></div>
      {!options.length && <p className="no-options">No observed options.</p>}
      {visible.map((option) => {
        const checked = selected.includes(option.value);
        return (
          <label key={option.value} className="filter-option">
            <input
              type="checkbox"
              name={`${type}-${title}`}
              data-condition-type={type}
              checked={checked}
              disabled={multiple && !checked && selected.length >= 4}
              onChange={(event) => onToggle(option.value, event.target.checked)}
            />
            <span>{option.value}</span><small>{formatPercent(option.usage)}</small>
          </label>
        );
      })}
      {expandable && options.length > 6 && (
        <button className="show-more" type="button" onClick={() => setExpanded((value) => !value)}>
          {expanded ? "Show less" : `Show more (${options.length - 6})`}
        </button>
      )}
    </section>
  );
}

interface Props {
  options: PokemonOptions;
  value: PokemonCondition;
  onChange: (value: PokemonCondition) => void;
  expandable?: boolean;
}

export function ConditionFilters({ options, value, onChange, expandable = false }: Props) {
  const toggleSingle = (type: "item" | "ability", option: string, checked: boolean) =>
    onChange({ ...value, [type]: checked ? option : null });

  return (
    <>
      <FilterGroup
        title="Moves"
        type="moves"
        options={options.moves}
        selected={value.moves}
        multiple
        expandable={expandable}
        onToggle={(option, checked) => onChange({
          ...value,
          moves: checked ? [...new Set([...value.moves, option])] : value.moves.filter((move) => move !== option),
        })}
        onClear={() => onChange({ ...value, moves: [] })}
      />
      <FilterGroup
        title="Item"
        type="item"
        options={options.items}
        selected={value.item ? [value.item] : []}
        expandable={expandable}
        onToggle={(option, checked) => toggleSingle("item", option, checked)}
        onClear={() => onChange({ ...value, item: null })}
      />
      <FilterGroup
        title="Ability"
        type="ability"
        options={options.abilities}
        selected={value.ability ? [value.ability] : []}
        expandable={expandable}
        onToggle={(option, checked) => toggleSingle("ability", option, checked)}
        onClear={() => onChange({ ...value, ability: null })}
      />
    </>
  );
}
