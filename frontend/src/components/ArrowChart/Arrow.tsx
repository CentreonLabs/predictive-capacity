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
