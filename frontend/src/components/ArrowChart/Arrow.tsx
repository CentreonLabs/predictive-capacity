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

type ArrowChartProps = {
  x1: number;
  x2: number;
  width: number;
  height: number;
};

const Arrow = ({ x1, x2, width, height }: ArrowChartProps) => {
  return (
    <svg
      xmlns="http://www.w3.org/2000/svg"
      viewBox={`0 0 ${width} ${height}`}
      width={width}
      height={height}
    >
      <line
        id="arrowline"
        x1={
          x1 <= x2
            ? x1 +
              (Number.isFinite(x1) &&
              Number.isFinite(x2) &&
              Math.abs(x1 - x2) < 10
                ? 0
                : 10)
            : x1 -
              (Number.isFinite(x1) &&
              Number.isFinite(x2) &&
              Math.abs(x1 - x2) < 10
                ? 0
                : 10)
        }
        y1={height / 2}
        x2={
          Number.isFinite(x1) && Number.isFinite(x2) && Math.abs(x1 - x2) < 10
            ? x1
            : x2
        }
        y2={height / 2}
      />
      <defs>
        <marker
          id="arrowhead"
          viewBox={`0 0 20 ${
            Number.isFinite(x1) && Number.isFinite(x2) && Math.abs(x1 - x2) < 10
              ? 30
              : 30
          }`}
          refX="5"
          refY="5"
          markerWidth="3"
          markerHeight="3"
          orient="auto-start-reverse"
        >
          <path d="M 0 0 L 5 5 L 0 10 z" />
        </marker>
      </defs>
      <line
        x1={x1}
        y1={height / 2}
        x2={x1}
        y2={height / 2}
        strokeWidth={20}
        markerStart={x1 < x2 ? "url(#arrowhead)" : undefined}
        markerEnd={x1 >= x2 ? "url(#arrowhead)" : undefined}
      />
    </svg>
  );
};

export default Arrow;
