// src/components/HumidityChart.js
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

export default function HumidityChart({ data = [], latest }) {
  const chartRef = useRef(null);
  if (!data.length) return null;

  // Humidity thresholds (% relative humidity)
 const thresholds = [
    { label: "Dry", max: 30, color: "blue" },
    { label: "Comfortable", max: 60, color: "green" },
    { label: "Humid", max: 80, color: "orange" },
  ];

  // If above last threshold, mark as Very Humid
  const activeLevel =
    thresholds.find((t) => latest <= t.max) || { label: "Very Humid", color: "red" };

  const chartData = {
    labels: data.map((d) => new Date(d.timestamp)),
    datasets: [
      {
        label: "Humidity (%)",
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
          label: (ctx) => `Humidity: ${ctx.parsed.y} %`,
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
        title: { display: true, text: "Humidity (%)" },
        beginAtZero: true,
        max: 100,
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
        Humidity — <span style={{ color: activeLevel.color }}>{activeLevel.label}</span>
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
        {thresholds.concat({ label: "Very Humid", color: "red" }).map((t) => (
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




