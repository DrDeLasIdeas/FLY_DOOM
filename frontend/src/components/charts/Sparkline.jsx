import React from "react";
import LineChart from "./LineChart.jsx";

export default function Sparkline({ values = [], color = "#22d3ee", height = 32 }) {
  return (
    <LineChart
      values={values}
      color={color}
      height={height}
      fill={false}
      placeholder=""
    />
  );
}
