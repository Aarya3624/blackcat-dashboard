import axios from "axios";
import React, { useState, useEffect } from "react";

const PeopleCounter: React.FC = () => {
  const [counts, setCounts] = useState({
    entered: 0,
    exited: 0,
    inside: 0,
  });

  useEffect(() => {
    const fetchCounts = async () => {
      try {
        const response = await fetch("http://127.0.0.1:8000/count");
        const data = await response.json();
        setCounts(data);
      } catch (error) {
        console.error("Error fetching counts: ", error);
      }
    };

    fetchCounts();
    const intervalId = setInterval(fetchCounts, 1000);

    return () => clearInterval(intervalId);
  }, []);

  return (
    <div className="flex flex-col w-full gap-2 h-full">
      <h1 className="text-3xl font-bold">People Counter</h1>

      <p className="text-xs text-gray-400">Welcome to your dashboard!</p>

      <div className="flex bg-grey-400 border border-grey-300 p-5 justify-center items-center w-2/3 mt-1 rounded-md flex-grow">
        <img
          style={{
            width: "100%",
            height: "450px",
            padding: "10px",
            borderRadius: "10px",
          }}
          src="http://127.0.0.1:8000/video_feed"
          alt="Video Feed"
        />
      </div>
      <div
        className="flex bg-grey-400 border border-grey-300 p-5 justify-evenly items-center w-2/3 mt-1 rounded-md gap-5"
        style={{
          height: "140px",
        }}
      >
        <div>Entered: {counts.entered}</div>
        <div>Exited: {counts.exited}</div>
        <div>Inside: {counts.inside}</div>
      </div>
    </div>
  );
};

export default PeopleCounter;
