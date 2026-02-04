// src/components/TempChart.js
import React, { useRef } from "react";
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Tooltip,
  Legend,
  TimeScale,
} from "chart.js";
import { Line } from "react-chartjs-2";
import zoomPlugin from "chartjs-plugin-zoom";
import annotationPlugin from "chartjs-plugin-annotation";
import "chartjs-adapter-date-fns";

ChartJS.register(
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Tooltip,
  Legend,
  TimeScale,
  zoomPlugin,
  annotationPlugin
);

export default function TempChart({ data = [], latest }) {
   const chartRef = useRef(null);
  if (!data.length) return null;

  // Temperature comfort thresholds (°C)
  const thresholds = [
    { label: "Cold", max: 18, color: "blue" },
    { label: "Comfortable", max: 24, color: "green" },
    { label: "Warm", max: 28, color: "orange" },
  ];

  // If above last threshold, mark as Hot
  const activeLevel =
    thresholds.find((t) => latest <= t.max) || { label: "Hot", color: "red" };

  const chartData = {
    labels: data.map((d) => new Date(d.timestamp)),
    datasets: [
      {
        label: "Temperature (°C)",
        data: data.map((d) => d.value),
        borderColor: activeLevel.color,
        backgroundColor: `${activeLevel.color}40`,
        pointRadius: 4,
        tension: 0.3,
      },
    ],
  };

  const chartOptions = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: { display: false },
      tooltip: {
        mode: "nearest",
        intersect: false,
        callbacks: {
          label: (ctx) => `Temp: ${ctx.parsed.y} °C`,
        },
      },
      annotation: {
        annotations: thresholds.map((t) => ({
          type: "line",
          yMin: t.max,
          yMax: t.max,
          borderColor: t.color,
          borderWidth: 2,
          borderDash: [6, 6],
          label: {
            content: t.label,
            enabled: true,
            position: "end",
            backgroundColor: `${t.color}20`,
            color: t.color,
          },
        })),
      },
      zoom: {
        zoom: {
          wheel: { enabled: true },
          pinch: { enabled: true },
          mode: "xy",
        },
        pan: { enabled: true, mode: "xy" },
      },
    },
    scales: {
      x: {
        type: "time",
        time: { unit: "minute", tooltipFormat: "p" },
        title: { display: true, text: "Time" },
        grid: { display: false },
      },
      y: {
        title: { display: true, text: "Temperature (°C)" },
        beginAtZero: false,
      },
    },
  };

  const lastUpdated = new Date(data[data.length - 1].timestamp).toLocaleTimeString();

  const handleResetZoom = () => {
    if (chartRef.current) chartRef.current.resetZoom();
  };

  return (
    <div
      style={{
        backgroundColor: "white",
        borderRadius: 12,
        padding: 20,
        marginBottom: 40,
        boxShadow: "0 2px 8px rgba(0,0,0,0.1)",
      }}
    >
      <h3 style={{ marginBottom: 10 }}>
        Temperature — <span style={{ color: activeLevel.color }}>{activeLevel.label}</span>
      </h3>

      {/* Legend */}
      <div
        style={{
          display: "flex",
          justifyContent: "center",
          gap: 20,
          marginBottom: 12,
          flexWrap: "wrap",
        }}
      >
        {thresholds.concat({ label: "Hot", color: "red" }).map((t) => (
          <div key={t.label}>
            <span style={{ color: t.color, fontWeight: "bold" }}>●</span> {t.label}
          </div>
        ))}
      </div>

      {/* Reset Zoom Button */}
      <div style={{ textAlign: "right", marginBottom: 8 }}>
        <button onClick={handleResetZoom}>Reset Zoom</button>
      </div>

      {/* Chart wrapper with fixed height */}
      <div style={{ height: 400 }}>
        <Line ref={chartRef} data={chartData} options={chartOptions} />
      </div>

      <p style={{ fontSize: 12, color: "#666", marginTop: 8 }}>
        Last updated: {lastUpdated}
      </p>
    </div>
  );
}



