import { SelectListbox } from "@/components/common/Select";
import {
  RESULTS_DASHBOARD_VALUE,
  type StageNavigationItem,
} from "../smallProject/dataEntry/stageNavigationOptions";

interface Props {
  options: StageNavigationItem[];
  collapsed: boolean;
  onChange: (value: string) => void;
}

export function ProjectStageSwitcher({ options, collapsed, onChange }: Props) {
  return (
    <div className={collapsed ? "mb-5 flex justify-center" : "mb-6"}>
      {!collapsed && (
        <div className="mb-2 text-xs font-medium uppercase tracking-wide text-text-faint">
          Project navigation
        </div>
      )}
      <SelectListbox
        value={RESULTS_DASHBOARD_VALUE}
        onChange={onChange}
        options={options}
        placeholder="Navigate project"
        className={collapsed ? "!w-10 !px-2" : "w-full"}
        aria-label="Project stage and dashboard"
        minMenuWidth={240}
      />
    </div>
  );
}
