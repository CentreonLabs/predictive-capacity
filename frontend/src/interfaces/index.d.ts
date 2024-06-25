// Copyright (C) 2024  Centreon
// This file is part of Predictive Capacity.
// This program is free software: you can redistribute it and/or modify
// it under the terms of the GNU Affero General Public License as published by
// the Free Software Foundation, either version 3 of the License, or
// (at your option) any later version.
//
// This program is distributed in the hope that it will be useful,
// but WITHOUT ANY WARRANTY; without even the implied warranty of
// MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
// GNU Affero General Public License for more details.
//
// You should have received a copy of the GNU Affero General Public License
// along with this program.  If not, see <http://www.gnu.org/licenses/>.

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
