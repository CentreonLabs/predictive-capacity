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
