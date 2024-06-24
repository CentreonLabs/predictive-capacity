import StarFilled from "./StarFilled";
import StarOutline from "./StarOutline";

export type ConfidenceProps = {
  confidenceLevel: 0 | 1 | 2;
  margin?: { top: number; right: number; bottom: number; left: number };
};

const ConfidenceLevel = ({ confidenceLevel }: ConfidenceProps) => {
  return (
    <>
      <svg width={72} height={40}>
        <rect x="0" y="0" width="72" height="24" fill="transparent" />
        <svg x="0" y="0" width="24" height="24" fill="red">
          <StarFilled />
        </svg>
        <svg x="24" y="0" width="24" height="24" fill="red">
          {confidenceLevel > 0 ? <StarFilled /> : <StarOutline />}
        </svg>
        <svg x="48" y="0" width="24" height="24" fill="red">
          {confidenceLevel > 1 ? <StarFilled /> : <StarOutline />}
        </svg>
      </svg>
    </>
  );
};

export default ConfidenceLevel;
