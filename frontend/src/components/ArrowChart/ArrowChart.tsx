import { LinePath, SplitLinePath } from "@visx/shape";
import { Text } from "@visx/text";
import { Group } from "@visx/group";
import { scaleLinear } from "@visx/scale";

import Arrow from "./Arrow";

type Point = { x: number; y: number };
const getX = (d: Point) => d.x;
const getY = (d: Point) => d.y;

export type ArrowChartProps = {
  width: number;
  height: number;
  currentSaturation: number;
  forecast: number;
  margin?: { top: number; right: number; bottom: number; left: number };
  events?: boolean;
};

const defaultMargin = { top: 15, left: 10, right: 10, bottom: 15 };

// scales
const xScale = scaleLinear<number>({
  domain: [0, 1],
  nice: true,
});

export const ArrowChart = ({
  width,
  height,
  currentSaturation,
  forecast,
  margin = defaultMargin,
}: ArrowChartProps) => {
  // bounds
  const xMax = width - margin.left - margin.right;
  const yMax = height - margin.top - margin.bottom;

  xScale.rangeRound([0, xMax]);

  return (
    <div>
      <svg width={width} height={height}>
        <rect width={width} height={height} fill={"var(--white)"} />

        <Group top={margin.top} left={margin.left}>
          <rect
            key={`background`}
            x={0}
            y={0}
            width={xMax}
            height={yMax}
            rx={0}
            fill={"var(--white)"}
            stroke={"var(--grey)"}
          />
          <rect
            key={`CurrentSaturationBar`}
            x={0}
            y={0}
            width={xScale(currentSaturation)}
            height={yMax}
            rx={0}
            fill={"var(--grey)"}
            stroke={"var(--grey)"}
          />
          <Text
            x={0}
            y={35}
            textAnchor="start"
            fill="var(--black)"
            fontSize={"clamp(10px, 5vw, 16px)"}
            fontWeight={700}
          >
            {Math.round(100 * currentSaturation)}
          </Text>
          <Text
            x={18}
            y={31}
            textAnchor="start"
            fill="var(--black)"
            fontSize={"clamp(8px, 5vw, 9px)"}
            fontWeight={700}
          >
            {"%"}
          </Text>
          {Math.abs(forecast - currentSaturation) < 0.02 && (
            <SplitLinePath
              segments={[
                [],
                [
                  { x: xScale(forecast), y: 0 },
                  { x: xScale(forecast), y: 24 },
                ],
              ]}
              sampleRate={1}
              segmentation="x"
              x={(d) => d.x}
              y={(d) => d.y}
              styles={[
                { stroke: "var(--blue)" },
                {
                  stroke: "transparent",
                  strokeWidth: 2,
                  strokeDasharray: "4",
                },
              ]}
            >
              {({ segment, styles, index }) =>
                index === 0 ? (
                  <path
                    id="_Color"
                    data-name=" ↳Color"
                    d="M0,0,5,5l5-5Z"
                    transform={`translate(${xScale(forecast) - 5} -5)`}
                    fill="var(--blue)"
                  />
                ) : (
                  <LinePath data={segment} x={getX} y={getY} {...styles} />
                )
              }
            </SplitLinePath>
          )}
          <Arrow
            x1={xScale(forecast)}
            x2={xScale(currentSaturation)}
            width={xMax}
            height={20}
          />
          <Text
            x={xScale(forecast)}
            y={0}
            dx={currentSaturation > forecast ? 30 : -17}
            dy={15}
            textAnchor="end"
            fill={"var(--white)"}
            fontSize={"clamp(10px, 5vw, 14px)"}
            fontWeight={700}
            angle={0}
          >
            {Math.round(100 * forecast)}
          </Text>
          <Text
            x={xScale(forecast)}
            y={-3}
            dx={currentSaturation > forecast ? 38 : -10}
            dy={15}
            textAnchor="end"
            fill={"var(--white)"}
            fontSize={"clamp(8px, 5vw, 9px)"}
            fontWeight={700}
            angle={0}
          >
            {"%"}
          </Text>
        </Group>
      </svg>
    </div>
  );
};
