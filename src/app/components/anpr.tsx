// import React, { useEffect, useState } from "react";
// import axios from "axios";

// interface Counts {
//   entered: { [key: string]: number };
//   exited: { [key: string]: number };
//   inside: { [key: string]: number };
// }

// const ANPR = () => {
//   const [counts, setCounts] = useState<Counts>({
//     entered: {},
//     exited: {},
//     inside: {},
//   });
//   const [cameraId, setCameraId] = useState("");
//   const [cameraLink, setCameraLink] = useState("");

//   useEffect(() => {
//     const interval = setInterval(() => {
//       axios.get("http://localhost:5000/count").then((response) => {
//         setCounts(response.data);
//       });
//     }, 1000);

//     return () => clearInterval(interval);
//   }, []);

//   const handleAddCamera = (cameraId: string, cameraLink: string) => {
//     axios
//       .post("http://localhost:5000/add_camera", {
//         camera_id: cameraId,
//         camera_link: cameraLink,
//       })
//       .then((response) => {
//         console.log(response.data);
//         // Trigger a re-fetch of counts to ensure the new camera appears
//         axios.get("http://localhost:5000/count").then((response) => {
//           setCounts(response.data);
//         });
//       })
//       .catch((error) => {
//         console.error("Error adding camera:", error);
//       });
//   };

//   const handleRemoveCamera = (cameraId: any) => {
//     axios
//       .post("http://localhost:5000/remove_camera", { camera_id: cameraId })
//       .then((response) => {
//         console.log(response.data);
//       })
//       .catch((error) => {
//         console.error("Error removing camera:", error);
//       });
//   };

//   return (
//     <div>
//       <h1 className="text-3xl font-bold">Dashboard</h1>
//       <div className="flex gap-2 flex-col w-1/3">
//         <h2>Add Camera</h2>
//         <input
//           type="text"
//           value={cameraId}
//           onChange={(e) => setCameraId(e.target.value)}
//           placeholder="Camera ID"
//           className="text-white rounded-md px-2 py-1 bg-grey-200 border-grey-200"
//         />
//         <input
//           type="text"
//           value={cameraLink}
//           onChange={(e) => setCameraLink(e.target.value)}
//           placeholder="Camera URL"
//           className="text-white rounded-md px-2 py-1 bg-grey-200 border-grey-200"
//         />
//         <button
//           className="bg-white text-black font-bold py-2 px-4 rounded"
//           onClick={() => handleAddCamera(cameraId, cameraLink)}
//         >
//           Add Camera
//         </button>
//       </div>
//       {Object.keys(counts.entered || {}).map((id) => (
//         <div key={id} style={{ display: "flex", flexDirection: "column" }}>
//           <h3>Camera {id}</h3>
//           <p>Entered: {counts.entered[id]}</p>
//           <p>Exited: {counts.exited[id]}</p>
//           <p>Inside: {counts.inside[id]}</p>
//           <img
//             src={`http://localhost:5000/video_feed/${id}`}
//             alt={`Camera ${id}`}
//             style={{ width: "640px", height: "480px" }}
//           />
//           <button onClick={() => handleRemoveCamera(id)}>Remove Camera</button>
//         </div>
//       ))}
//     </div>
//   );
// };

// export default ANPR;

import React, { useEffect, useState, useRef } from "react";
import axios from "axios";
import io from "socket.io-client";

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
      setCounts(count);
    });

    // Fetch initial counts when the component mounts
    axios.get("http://localhost:5000/count").then((response) => {
      setCounts(response.data);
    });

    return () => {
      if (socketRef.current) {
        socketRef.current.disconnect();
      }
    };
  }, []);

  const handleAddCamera = (cameraId: string, cameraLink: string) => {
    axios
      .post("http://localhost:5000/add_camera", {
        camera_id: cameraId,
        camera_link: cameraLink,
      })
      .then((response) => {
        console.log(response.data);
        setCameraId("");
        setCameraLink("");
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
        setCounts((prevCounts) => {
          // Create a new object excluding the cameraId key from entered, exited, and inside
          const {
            entered: { [cameraId]: removedEntered, ...updatedEntered },
            exited: { [cameraId]: removedExited, ...updatedExited },
            inside: { [cameraId]: removedInside, ...updatedInside },
          } = prevCounts;

          return {
            entered: updatedEntered,
            exited: updatedExited,
            inside: updatedInside,
          };
        });
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
            className="border border-grey-300 p-5 justify-center items-center mt-1 rounded-md"
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
            <button onClick={() => handleRemoveCamera(id)}>
              Remove Camera
            </button>
          </div>
        ))}
      </div>
    </div>
  );
};

export default ANPR;
