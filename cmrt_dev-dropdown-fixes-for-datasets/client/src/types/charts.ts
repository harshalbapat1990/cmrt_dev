

export interface AxisConfig {
  title?: string;
  min?: number;
  max?: number;
  stepSize?: number;
  grid?: boolean;
  position?: "top" | "bottom" | "left" | "right";
  tickFormatter?: (value: number) => string; 
}

export interface LegendConfig {
  show?: boolean;
  position?: "top" | "bottom" | "left" | "right";
  boxShape?: "square" | "circle";
}

export interface DatasetConfig {
  label: string;
  values: number[];
  color: string;
  
  barThickness?: number;
  categoryPercentage?: number;
  barPercentage?: number;

}


export interface DoughnutCenterText {
  text: string;
  subText?: string;
}


export interface RangeDatasetConfig {
  label: string;
  ranges: [number, number][]; 
  color: string;
}
import {
  Chart as ChartJS,
  Tooltip,
  Legend,
} from "chart.js";
import { TreemapController, TreemapElement } from "chartjs-chart-treemap";

ChartJS.register(
  Tooltip,
  Legend,
  TreemapController,
  TreemapElement
);
