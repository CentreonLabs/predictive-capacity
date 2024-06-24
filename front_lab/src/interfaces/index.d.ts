export interface ICategory {
  id: number;
  title: string;
}
export interface IPost {
  id: number;
  title: string;
  content: string;
  status: "published" | "draft" | "rejected";
  createdAt: string;
  category: { id: number };
}

export interface IMetric {
  uuid: string;
  metric_name: string;
  host_name: string;
  host_id: string;
  service_id: string;
  service_name: string;
  days_to_full: number;
  current_saturation: number;
  confidence_level: number;
  saturation_3_months: {
    current_saturation: number;
    forecast: number;
  };
  saturation_6_months: {
    current_saturation: number;
    forecast: number;
  };
  saturation_12_months: {
    current_saturation: number;
    forecast: number;
  };
}

export * from "./IDatacontext";
