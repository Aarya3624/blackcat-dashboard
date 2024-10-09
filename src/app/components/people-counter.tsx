import React, { useEffect, useState, useRef } from "react";
import axios from "axios";
import io from "socket.io-client";

interface Counts {
  entered: { [key: string]: number };
  exited: { [key: string]: number };
  inside: { [key: string]: number };
}

const PeopleCounter = () => {
  const [counts, setCounts] = useState<Counts>({
    entered: {},
    exited: {},
    inside: {},
  });
  const [cameraId, setCameraId] = useState("");
  const [cameraLink, setCameraLink] = useState("");
  const [hallId, setHallId] = useState("");
  const [halls, setHalls] = useState<{ [key: string]: Counts }>({});
  const [activeTab, setActiveTab] = useState("hall-1"); // Default active tab
  const socketRef = useRef<any>();

  useEffect(() => {
    socketRef.current = io("http://localhost:5000/video", {
      transports: ["websocket"],
    });

    socketRef.current.on("connect", () => {
      console.log("Connected to server");
    });

    socketRef.current.on("video_feed", (data: any) => {
      const { camera_id, frame } = data;
      const image = document.getElementById(
        `camera-${camera_id}`
      ) as HTMLImageElement;
      if (image) {
        image.src = `data:image/jpeg;base64,${frame}`;
      }
    });

    socketRef.current.on("count", (data: any) => {
      const { count } = data;
      setHalls(count);
      // Update individual counts for the active tab
      setCounts(count[activeTab] || { entered: {}, exited: {}, inside: {} });
    });

    // Fetch initial counts and halls when the component mounts
    axios.get("http://localhost:5000/halls").then((response) => {
      setHalls(response.data);
      setCounts(
        response.data[activeTab] || { entered: {}, exited: {}, inside: {} }
      );
    });

    return () => {
      if (socketRef.current) {
        socketRef.current.disconnect();
      }
    };
  }, [activeTab]);

  useEffect(() => {});

  const handleAddCamera = (
    cameraId: string,
    cameraLink: string,
    hallId: string
  ) => {
    axios
      .post("http://localhost:5000/add_camera", {
        camera_id: cameraId,
        camera_link: cameraLink,
        hall_id: hallId,
      })
      .then((response) => {
        console.log(response.data);
        setCameraId("");
        setCameraLink("");
        setHallId("");
      })
      .catch((error) => {
        console.error("Error adding camera:", error);
      });
  };

  const handleRemoveCamera = (cameraId: any, hallId: string) => {
    axios
      .post("http://localhost:5000/remove_camera", {
        camera_id: cameraId,
        hall_id: hallId,
      })
      .then((response) => {
        console.log(response.data);
      })
      .catch((error) => {
        console.error("Error removing camera:", error);
      });
  };

  return (
    <div className="bg-black">
      <h1 className="text-3xl font-bold">People Counter</h1>

      {/* Tabs */}
      <div className="flex gap-4 mb-4">
        {Object.keys(halls).map((hall) => (
          <button
            key={hall}
            className={`px-4 py-2 rounded-md ${
              activeTab === hall
                ? "bg-blue-500 text-white"
                : "bg-gray-200 text-gray-800"
            }`}
            onClick={() => setActiveTab(hall)}
          >
            {hall}
          </button>
        ))}
      </div>

      <div className="flex gap-2 flex-col w-1/3">
        <h2>Add Camera</h2>
        <input
          type="text"
          value={cameraId}
          onChange={(e) => setCameraId(e.target.value)}
          placeholder="Camera ID"
          className="text-white rounded-md px-2 py-1 bg-grey-200 border-gray-200"
        />
        <input
          type="text"
          value={hallId}
          onChange={(e) => setHallId(e.target.value)}
          placeholder="Hall ID"
          className="text-white rounded-md px-2 py-1 bg-grey-200 border-gray-200"
        />
        <input
          type="text"
          value={cameraLink}
          onChange={(e) => setCameraLink(e.target.value)}
          placeholder="Camera URL"
          className="text-white rounded-md px-2 py-1 bg-grey-200 border-gray-200"
        />
        <button
          className="bg-white text-black font-bold py-2 px-4 rounded"
          onClick={() => handleAddCamera(cameraId, cameraLink, hallId)}
        >
          Add Camera
        </button>
      </div>

      <div
        style={{
          display: "flex",
          flexDirection: "column",
          flexWrap: "wrap",
          gap: "20px",
        }}
      >
        {Object.keys(counts.entered || {}).map((id) => (
          <div
            className="border border-gray-300 p-5 justify-center items-center mt-1 rounded-md"
            key={id}
            style={{
              display: "flex",
              flexDirection: "row",
              gap: "10px",
              alignItems: "center",
              padding: "10px",
              borderWidth: 1,
              borderRadius: "5px",
              backgroundColor: "#252525",
            }}
          >
            <h3>Camera {id}</h3>
            <p>Entered: {counts.entered[id]}</p>
            <p>Exited: {counts.exited[id] || 0}</p>
            <p>Inside: {counts.inside[id] || 0}</p>
            <img
              id={`camera-${id}`}
              alt={`Camera ${id}`}
              style={{ width: "400px", height: "300px" }}
            />
            <button onClick={() => handleRemoveCamera(id, activeTab)}>
              Remove Camera
            </button>
          </div>
        ))}
      </div>
    </div>
  );
};

export default PeopleCounter;
