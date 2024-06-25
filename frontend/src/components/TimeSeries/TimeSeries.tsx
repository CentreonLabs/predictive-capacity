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

import React, { useRef, useState, useMemo, useCallback } from "react";
import { scaleTime, scaleLinear } from "@visx/scale";
import { Line } from "@visx/shape";
import { Group } from "@visx/group";
import { min, max, extent } from "d3-array";
import { Typography, Row, Col } from "antd";

import {
  Tooltip,
  TooltipWithBounds,
  useTooltip,
  defaultStyles,
} from "@visx/tooltip";
import { voronoi } from "@visx/voronoi";
import { localPoint } from "@visx/event";

import { timeFormat } from "d3-time-format";

import LineChart from "./LineChart";
const { Text } = Typography;

interface Metric {
  date: Date;
  value: number;
}

// Initialize some variables
export const accentColor = "#aaa";
export const accentColorDark = "rgba(53,71,125,0.2)";
export const background = "#aaa";
export const background2 = "#aaa";

const tooltipStyles = {
  ...defaultStyles,
  backgroundColor: "rgba(53,71,125,0.8)",
  color: "white",
  fontFamily: "Exo 2, sans-serif",
  fontSize: "clamp(12px, 2.2vw, 15px)",
  fontWeight: 500,
  padding: "0.5rem 0.7rem 0.5rem 0.7rem",
  borderRadius: 10,
};
const formatDate = timeFormat("%b %d, %Y");

// accessors
const getDate = (d: any) => new Date(d.date);
const getMetricValue = (d: Metric) => d.value;

type TooltipData = { date: any; value: number };
type PointsRange = { date: any; value: number };

let tooltipTimeout: number;

export type TimeSeriesProps = {
  width: number;
  height: number;
  margin?: { top: number; right: number; bottom: number; left: number };
  compact?: boolean;
  record?: any;
};

function TimeSeries({
  record,
  compact = false,
  width,
  height,
  margin = {
    top: 50,
    left: 80,
    bottom: 20,
    right: 20,
  },
}: TimeSeriesProps) {
  const svgRef = useRef<SVGSVGElement>(null);

  const metric: Metric[] = record?.data_scaled.map(
    (val: number, ind: number) => ({
      value: val,
      date: new Date(record?.data_dates[ind]),
    })
  );

  const forecast: Metric[] = record?.forecast.map(
    (val: number, ind: number) => ({
      value: val,
      date: new Date(record?.forecast_dates[ind]),
    })
  );

  const [filteredMetric, setFilteredMetric] = useState(metric);
  const [filteredForecast, setFilteredForecast] = useState(forecast);

  const legendGlyphSize = 15;
  // bounds
  const xMax = Math.max(width - margin.left - margin.right, 0);
  const yMax = Math.max(height - margin.top - margin.bottom, 0);

  // scales

  const dateScale = useMemo(
    () =>
      scaleTime<number>({
        range: [0, xMax],
        domain: [
          extent(filteredMetric, getDate)[0],
          extent(filteredForecast, getDate)[1],
        ] as [Date, Date],
      }),
    [xMax, filteredMetric, filteredForecast]
  );

  const metricScale = useMemo(
    () =>
      scaleLinear<number>({
        range: [yMax, 0],
        domain: [
          Math.min(
            min(filteredMetric, getMetricValue) || 0,
            min(filteredForecast, getMetricValue) || 0
          ),
          Math.max(
            max(filteredMetric, getMetricValue) || 0,
            max(filteredForecast, getMetricValue) || 0
          ),
        ],
        nice: true,
      }),
    [yMax, filteredMetric, filteredForecast]
  );

  const voronoiLayout = useMemo(
    () =>
      voronoi<PointsRange>({
        x: (d: any) => dateScale(getDate(d)) ?? 0,
        y: (d: any) => 0,
        width: xMax,
        height: yMax,
      })([...filteredMetric, ...filteredForecast]),
    [xMax, yMax, dateScale, filteredMetric, filteredForecast]
  );

  const {
    showTooltip,
    hideTooltip,
    tooltipData,
    tooltipLeft = 0,
    tooltipTop = 0,
  } = useTooltip<TooltipData>({
    // initial tooltip state
    tooltipOpen: false,
    tooltipLeft: xMax,
    tooltipTop: yMax / 3,
  });

  // event handlers

  const handleMouseMove = useCallback(
    (event: React.MouseEvent | React.TouchEvent) => {
      if (tooltipTimeout) clearTimeout(tooltipTimeout);

      if (!svgRef.current) return;

      // find the nearest polygon to the current mouse position
      const point = localPoint(svgRef.current, event);
      if (!point) return;
      const neighborRadius = 200;
      const closest = voronoiLayout.find(
        point.x - margin.left,
        0,
        neighborRadius
      );

      if (closest) {
        showTooltip({
          tooltipLeft: dateScale(getDate(closest.data)),
          tooltipTop: metricScale(getMetricValue(closest.data)),
          tooltipData: closest.data,
        });
      }
    },
    [dateScale, metricScale, showTooltip, voronoiLayout, margin]
  );

  const handleMouseLeave = useCallback(() => {
    tooltipTimeout = window.setTimeout(() => {
      hideTooltip();
    }, 300);
  }, [hideTooltip]);

  return (
    <div style={{ userSelect: "none" }}>
      <Row>
        <Col span={1}>
          <svg width={legendGlyphSize} height={legendGlyphSize}>
            <rect
              fill={"dodgerblue"}
              width={legendGlyphSize}
              height={legendGlyphSize}
            />
          </svg>
        </Col>
        <Col span={4}>
          <Text> metric</Text>
        </Col>
        <Col span={1}>
          <svg width={legendGlyphSize} height={legendGlyphSize}>
            <rect
              fill={"green"}
              width={legendGlyphSize}
              height={legendGlyphSize}
            />
          </svg>
        </Col>
        <Col span={4}>
          <Text> forecast</Text>
        </Col>
      </Row>
      <svg width={width} height={height}>
        <LineChart
          hideBottomAxis={compact}
          data={filteredMetric}
          dataForecast={filteredForecast}
          width={width}
          margin={margin}
          yMax={yMax}
          xScale={dateScale}
          yScale={metricScale}
          gradientColor={background2}
        />
        <Group left={margin.left} top={margin.top}>
          <svg width={width} height={height} ref={svgRef}>
            <rect
              x={0}
              y={0}
              width={xMax}
              height={yMax}
              rx={5}
              fill="transparent"
              stroke="transparent"
              onMouseMove={handleMouseMove}
              onMouseLeave={handleMouseLeave}
              onTouchMove={handleMouseMove}
              onTouchEnd={handleMouseLeave}
            />
            {tooltipData && (
              <g>
                <Line
                  from={{ x: tooltipLeft, y: 0 }}
                  to={{ x: tooltipLeft, y: yMax }}
                  stroke={accentColorDark}
                  strokeWidth={1}
                  pointerEvents="none"
                  strokeDasharray="4,4"
                />
                <Line
                  from={{ x: 0, y: tooltipTop }}
                  to={{ x: xMax, y: tooltipTop }}
                  stroke={accentColorDark}
                  strokeWidth={1}
                  pointerEvents="none"
                  strokeDasharray="4,4"
                />
                <circle
                  cx={tooltipLeft}
                  cy={tooltipTop}
                  r={10}
                  fill="accentColorDark"
                  fillOpacity={0.1}
                  stroke="black"
                  strokeOpacity={0.1}
                  strokeWidth={2}
                  pointerEvents="none"
                />
                <circle
                  cx={tooltipLeft}
                  cy={tooltipTop}
                  r={4}
                  fill={accentColorDark}
                  stroke="white"
                  strokeWidth={2}
                  pointerEvents="none"
                />
              </g>
            )}
          </svg>
        </Group>
      </svg>
      {tooltipData && (
        <>
          <TooltipWithBounds
            key={Math.random()}
            top={tooltipTop + margin.top}
            left={tooltipLeft + margin.left}
            style={tooltipStyles}
          >
            {`${(100 * getMetricValue(tooltipData)).toFixed(2)}%`}
          </TooltipWithBounds>
          <Tooltip
            top={height}
            left={tooltipLeft + margin.left}
            style={{
              ...defaultStyles,
              minWidth: 72,
              textAlign: "center",
              transform: "translateX(-50%)",
            }}
          >
            {formatDate(getDate(tooltipData))}
          </Tooltip>
        </>
      )}
    </div>
  );
}

export default TimeSeries;
