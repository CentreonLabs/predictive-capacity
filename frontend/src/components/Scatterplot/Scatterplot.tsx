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

import React, { useMemo, useCallback, useRef } from "react";
import { Group } from "@visx/group";
import { LinearGradient } from "@visx/gradient";
import { AxisLeft, AxisBottom } from "@visx/axis";
import { scaleLinear, scaleThreshold } from "@visx/scale";
import { withTooltip, Tooltip, defaultStyles } from "@visx/tooltip";
import { WithTooltipProvidedProps } from "@visx/tooltip/lib/enhancers/withTooltip";
import { voronoi } from "@visx/voronoi";
import { localPoint } from "@visx/event";
import { GridRows, GridColumns } from "@visx/grid";
import { min, max } from "d3-array";

export type DataRecord = {
  current_saturation: number;
  //days_to_full: number;
  neg_days_to_full: number;
  key: React.Key;
  host_name: string;
  service_name: string;
};

const x = (d: DataRecord) => d["neg_days_to_full"];
const y = (d: DataRecord) => d["current_saturation"];
const serviceName = (d: DataRecord) => d["service_name"];
const hostName = (d: DataRecord) => d["host_name"];

export type DotsProps = {
  width: number;
  height: number;
  showControls?: boolean;
  margin?: any;
  data?: any;
  selectedRowKeys?: React.Key[];
  setSelectedRowKeys?: any;
};

let tooltipTimeout: number;

const backgroundColor = "#8894AA";
const criticalColor = "#FF5D52";
const normalColor = "#57A773";
const warningColor = "#ECC30B";

const axisColor = "#fff";
const axisStroke = "#fff";

const axisBottomTickLabelProps = {
  textAnchor: "middle" as const,
  fontSize: "clamp(10px, 2.2vw, 12px)",
  fontWeight: 400,
  fill: axisColor,
};
const axisBottomLabelProps = {
  dx: "2em",
  dy: "1em",
  textAnchor: "middle" as const,
  fontSize: "clamp(10px, 2.2vw, 14px)",
  fontWeight: 400,
  fill: axisColor,
};
const axisLeftTickLabelProps = {
  dx: "0em",
  dy: "0.2em",
  textAnchor: "end" as const,
  fill: axisColor,
  fontSize: "clamp(10px, 2.2vw, 12px)",
  fontWeight: 400,
};

const axisLeftLabelProps = {
  dx: "-2.2em",
  dy: "0em",
  textAnchor: "middle" as const,
  fill: axisColor,
  fontSize: "clamp(10px, 2.2vw, 14px)",
  fontWeight: 400,
};

const defaultMargin = { top: 30, left: 100, right: 40, bottom: 50 };

const tooltipStyle = {
  ...defaultStyles,
  backgroundColor: "#5D6A83",
  color: "white",
  fontSize: "clamp(10px, 2.2vw, 12px)",
  borderRadius: "3px",
  lineHeight: "16px",
  zIndex: 3,
};

export default withTooltip<DotsProps, DataRecord>(
  ({
    data,
    width,
    height,
    showControls = true,
    margin = defaultMargin,
    hideTooltip,
    showTooltip,
    tooltipOpen,
    tooltipData,
    tooltipLeft,
    tooltipTop,
    selectedRowKeys,
    setSelectedRowKeys,
  }: DotsProps & WithTooltipProvidedProps<DataRecord>) => {
    if (width < 10) return null;
    const svgRef = useRef<SVGSVGElement>(null);

    const xMax = width - margin.left - margin.right;
    const yMax = height - margin.top - margin.bottom;

    const xScale = useMemo(
      () =>
        data &&
        scaleLinear<number>({
          domain: [min(data, x) || 0, max(data, x) || 0],
          range: [0, xMax],
          clamp: true,
          nice: true,
          round: true,
        }),
      [xMax, data]
    );
    const yScale = useMemo(
      () =>
        data &&
        scaleLinear<number>({
          domain: [min(data, y) || 0, max(data, y) || 0],
          range: [yMax, 0],
          clamp: true,
          nice: true,
          //round: true,
        }),
      [yMax, data]
    );

    const colorScale = scaleThreshold<number, string>({
      domain: [-50, -10],
      range: [normalColor, warningColor, criticalColor],
    });

    const voronoiLayout = useMemo(
      () =>
        data &&
        voronoi<DataRecord>({
          x: (d) => xScale(x(d)) ?? 0,
          y: (d) => yScale(y(d)) ?? 0,
          width: xMax,
          height: yMax,
        })(data),
      [xMax, yMax, xScale, yScale, data]
    );

    // event handlers
    const handleMouseMove = useCallback(
      (event: React.MouseEvent | React.TouchEvent) => {
        if (tooltipTimeout) clearTimeout(tooltipTimeout);
        if (!svgRef.current) return;

        // find the nearest polygon to the current mouse position
        const point = localPoint(svgRef.current, event);
        if (!point) return;
        const neighborRadius = 100;
        const closest =
          voronoiLayout &&
          voronoiLayout.find(
            point.x - margin.left,
            point.y - margin.top,
            neighborRadius
          );
        if (closest) {
          showTooltip({
            tooltipLeft: xScale(x(closest.data)),
            tooltipTop: yScale(y(closest.data)),
            tooltipData: closest.data,
          });
        }
      },
      [xScale, yScale, showTooltip, voronoiLayout, margin.left, margin.top]
    );

    const handleMouseLeave = useCallback(() => {
      tooltipTimeout = window.setTimeout(() => {
        hideTooltip();
      }, 300);
    }, [hideTooltip]);

    const handleClick = useCallback(
      (event: React.MouseEvent | React.TouchEvent) => {
        if (tooltipTimeout) clearTimeout(tooltipTimeout);
        if (!svgRef.current) return;

        // find the nearest polygon to the current mouse position
        const point = localPoint(svgRef.current, event);
        if (!point) return;
        const neighborRadius = 50;
        const closest =
          voronoiLayout &&
          voronoiLayout.find(
            point.x - margin.left,
            point.y - margin.top,
            neighborRadius
          );
        if (closest) {
          setSelectedRowKeys([closest.data["key"]]);
        }
      },
      [voronoiLayout, margin.left, margin.top, setSelectedRowKeys]
    );

    return (
      <div>
        <svg width={width} height={height} ref={svgRef}>
          <defs>
            <filter id="shadow">
              <feDropShadow
                dx="0.2"
                dy="0.6"
                stdDeviation="2"
                floodColor="white"
              />
            </filter>
          </defs>
          <LinearGradient
            id="dots-pink"
            from={backgroundColor}
            to={backgroundColor}
            toOpacity={0.7}
            rotate={-3}
          />
          {/** capture all mouse events with a rect */}
          <rect
            width={width}
            height={height}
            rx={5}
            fill="url(#dots-pink)"
            onMouseMove={handleMouseMove}
            onMouseLeave={handleMouseLeave}
            onTouchMove={handleMouseMove}
            onTouchEnd={handleMouseLeave}
            onClick={handleClick}
          />

          <Group pointerEvents="none" left={margin.left} top={margin.top}>
            {yScale && (
              <GridRows
                scale={yScale}
                width={xMax}
                numTicks={5}
                stroke={"#fff"}
                strokeOpacity={0.6}
                strokeWidth={1}
                pointerEvents="none"
              />
            )}
            {xScale && (
              <GridColumns
                scale={xScale}
                height={yMax}
                numTicks={Math.ceil(width / 150)}
                stroke={"#fff"}
                strokeOpacity={0.6}
                strokeWidth={1}
                pointerEvents="none"
              />
            )}
            {xScale && (
              <AxisBottom
                top={yMax}
                rangePadding={0}
                scale={xScale}
                hideTicks={true}
                numTicks={Math.ceil(width / 150)}
                tickFormat={(v: any) => v.toFixed(0) + "d"}
                stroke={axisStroke}
                tickStroke={axisColor}
                tickLabelProps={() => axisBottomTickLabelProps}
                label={"Days to full Capacity"}
                labelProps={axisBottomLabelProps}
              />
            )}
            {yScale && (
              <AxisLeft
                left={0}
                scale={yScale}
                rangePadding={0}
                hideTicks={true}
                numTicks={Math.ceil(height / 80)}
                tickFormat={(v: any) => (100 * v).toFixed(2) + "%"}
                stroke={axisStroke}
                tickStroke={axisColor}
                tickLabelProps={() => axisLeftTickLabelProps}
                label={"Percantage"}
                labelProps={axisLeftLabelProps}
              />
            )}
            {data &&
              data?.map((point: DataRecord, i: number) => (
                <circle
                  key={`point-${point["key"]}-${i}`}
                  className="dot"
                  cx={xScale(x(point))}
                  cy={yScale(y(point))}
                  r={
                    selectedRowKeys && selectedRowKeys[0] === point["key"]
                      ? "12px"
                      : "8px"
                  }
                  fill={
                    point && tooltipData === point
                      ? "white"
                      : colorScale(x(point))
                  }
                  filter={
                    selectedRowKeys && selectedRowKeys[0] === point["key"]
                      ? "url(#shadow)"
                      : undefined
                  }
                  stroke={"#fff"}
                  strokeWidth={"1px"}
                  onClick={(e) => {
                    setSelectedRowKeys(point["key"]);
                    e.preventDefault();
                  }}
                />
              ))}
          </Group>
        </svg>
        {tooltipOpen &&
          tooltipData &&
          tooltipLeft != null &&
          tooltipTop != null && (
            <Tooltip
              left={tooltipLeft + margin.left + 5}
              top={tooltipTop + margin.top + 5}
              style={tooltipStyle}
            >
              <div>
                <strong> Host Name </strong>
                {"  "}
                {hostName(tooltipData)}
              </div>
              <div>
                <strong> Service</strong>
                {"  "}
                {serviceName(tooltipData)}
              </div>
              <div>
                <strong> Saturation </strong>
                {"  "}
                {(100 * y(tooltipData)).toFixed(2) + "%"}
              </div>
              <div>
                <strong> Days to full capacity </strong>
                {"  "}
                {x(tooltipData).toFixed(0) + "d"}
              </div>
            </Tooltip>
          )}
      </div>
    );
  }
);
