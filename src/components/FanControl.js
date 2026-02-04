// src/components/FanControl.js
import React from "react";

const FanControl = ({ status, onToggle }) => (
  <div style={{ border: "1px solid #ccc", padding: "10px", borderRadius: "10px", marginBottom: "20px" }}>
    <h3>Fan</h3>
    <p>Status: {status ? "ON" : "OFF"}</p>
    <button onClick={onToggle}>{status ? "Turn OFF" : "Turn ON"}</button>
  </div>
);

export default FanControl;


