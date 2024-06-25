import React from "react";
import { Group } from "@visx/group";
import { LinePath } from "@visx/shape";
import { AxisLeft, AxisBottom, AxisScale } from "@visx/axis";
import { LinearGradient } from "@visx/gradient";
import { curveLinear } from "@visx/curve";
import { GridRows, GridColumns } from "@visx/grid";
// import { timeFormat } from "d3-time-format";

// Initialize some variables
const axisColor = "rgba(2,2,4,0.6)";
const axisStroke = "#fff";
const axisBottomTickLabelProps = {
  textAnchor: "middle" as const,
  fontSize: "clamp(12px, 2.2vw, 15px)",
  fontWeight: 500,
  fill: axisColor,
};

const axisLeftTickLabelProps = {
  dx: "-0.1em",
  dy: "0.25em",
  textAnchor: "end" as const,
  fill: axisColor,
  fontSize: "clamp(12px, 2.2vw, 15px)",
  fontWeight: 400,
};

interface Metric {
  date: Date;
  value: number;
}
// accessors
const getDate = (d: any) => new Date(d.date);
const getMetricValue = (d: Metric) => d.value;

export default function LineChart({
  data,
  dataForecast,
  gradientColor,
  width,
  yMax,
  margin,
  xScale,
  yScale,
  hideBottomAxis = false,
  hideLeftAxis = false,
  top,
  left,
  children,
}: {
  data: Metric[];
  dataForecast: Metric[];
  gradientColor: string;
  xScale: AxisScale<number>;
  yScale: AxisScale<number>;
  width: number;
  yMax: number;
  margin: { top: number; right: number; bottom: number; left: number };
  hideBottomAxis?: boolean;
  hideLeftAxis?: boolean;
  top?: number;
  left?: number;
  children?: React.ReactNode;
}) {
  if (width < 20) return null;

  return (
    <Group left={left || margin.left} top={top || margin.top}>
      <LinearGradient
        id="gradient"
        from={gradientColor}
        fromOpacity={1}
        to={gradientColor}
        toOpacity={0.2}
      />
      {!hideLeftAxis && (
        <GridRows
          scale={yScale}
          width={width - margin.left - margin.right}
          numTicks={5}
          stroke={"black"}
          strokeOpacity={0.1}
          strokeWidth={1}
          pointerEvents="none"
        />
      )}
      {!hideBottomAxis && (
        <GridColumns
          scale={xScale}
          height={yMax}
          width={width - margin.left - margin.right}
          numTicks={4}
          stroke={"black"}
          strokeOpacity={0.1}
          strokeWidth={1}
          pointerEvents="none"
        />
      )}
      <LinePath<Metric>
        data={data}
        x={(d) => xScale(getDate(d)) || 0}
        y={(d) => yScale(getMetricValue(d)) || 0}
        curve={curveLinear}
        stroke="dodgerblue"
        strokeWidth={2}
        strokeOpacity={0.6}
      />
      <LinePath<Metric>
        data={dataForecast}
        x={(d) => xScale(getDate(d)) || 0}
        y={(d) => yScale(getMetricValue(d)) || 0}
        curve={curveLinear}
        stroke="green"
        strokeWidth={2}
        strokeOpacity={0.6}
      />
      {!hideBottomAxis && (
        <AxisBottom
          top={yMax}
          scale={xScale}
          hideTicks={true}
          numTicks={Math.ceil(width / 140)}
          stroke={axisStroke}
          tickStroke={axisColor}
          tickLabelProps={() => axisBottomTickLabelProps}
        />
      )}
      {!hideLeftAxis && (
        <AxisLeft
          scale={yScale}
          hideTicks={true}
          numTicks={Math.ceil(yMax / 100)}
          tickFormat={(v: number) => (100 * v).toFixed(2) + "%"}
          stroke={axisStroke}
          tickStroke={axisColor}
          tickLabelProps={() => axisLeftTickLabelProps}
        />
      )}
      {children}
    </Group>
  );
}
