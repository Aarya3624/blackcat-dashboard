import React, { useEffect, useState } from "react";
import axios from "axios";

interface Counts {
  entered: { [key: string]: number };
  exited: { [key: string]: number };
  inside: { [key: string]: number };
}

const ANPR = () => {
  const [counts, setCounts] = useState<Counts>({
    entered: {},
    exited: {},
    inside: {},
  });
  const [cameraId, setCameraId] = useState("");
  const [cameraLink, setCameraLink] = useState("");

  useEffect(() => {
    const interval = setInterval(() => {
      axios.get("http://localhost:5000/count").then((response) => {
        setCounts(response.data);
      });
    }, 1000);

    return () => clearInterval(interval);
  }, []);

  const handleAddCamera = (cameraId: any, cameraLink: any) => {
    axios
      .post("http://localhost:5000/add_camera", {
        camera_id: cameraId,
        camera_link: cameraLink,
      })
      .then((response) => {
        console.log(response.data);
      })
      .catch((error) => {
        console.error("Error adding camera:", error);
      });
  };

  const handleRemoveCamera = (cameraId: any) => {
    axios
      .post("http://localhost:5000/remove_camera", { camera_id: cameraId })
      .then((response) => {
        console.log(response.data);
      })
      .catch((error) => {
        console.error("Error removing camera:", error);
      });
  };

  return (
    <div>
      <h1 className="text-3xl font-bold">Dashboard</h1>
      <div className="flex gap-2 flex-col w-1/3">
        <h2>Add Camera</h2>
        <input
          type="text"
          value={cameraId}
          onChange={(e) => setCameraId(e.target.value)}
          placeholder="Camera ID"
          className="text-white rounded-md px-2 py-1 bg-grey-200 border-grey-200"
        />
        <input
          type="text"
          value={cameraLink}
          onChange={(e) => setCameraLink(e.target.value)}
          placeholder="Camera URL"
          className="text-white rounded-md px-2 py-1 bg-grey-200 border-grey-200"
        />
        <button
          className="bg-white text-black font-bold py-2 px-4 rounded"
          onClick={() => handleAddCamera(cameraId, cameraLink)}
        >
          Add Camera
        </button>
      </div>
      {Object.keys(counts.entered || {}).map((id) => (
        <div key={id}>
          <h3>Camera {id}</h3>
          <p>Entered: {counts.entered[id]}</p>
          <p>Exited: {counts.exited[id]}</p>
          <p>Inside: {counts.inside[id]}</p>
          <img
            src={`http://localhost:5000/video_feed/${id}`}
            alt={`Camera ${id}`}
          />
          <button onClick={() => handleRemoveCamera(id)}>Remove Camera</button>
        </div>
      ))}
    </div>
  );
};

export default ANPR;
