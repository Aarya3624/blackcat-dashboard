import React, { useState, useEffect } from "react";

const ANPR: React.FC = () => {
  return (
    <div>
      <h1 className="text-3xl font-bold">ANPR</h1>
      <div style={{ position: "relative", display: "inline-block" }}>
        <img
          src="http://127.0.0.1:5000/video_feed"
          alt="Video Feed"
          style={{ width: "100%", height: "auto" }}
        />
      </div>
    </div>
  );
};

export default ANPR;
