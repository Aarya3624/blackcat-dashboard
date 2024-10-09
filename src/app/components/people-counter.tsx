// import React, { useEffect, useState, useRef } from "react";
// import axios from "axios";
// import io from "socket.io-client";
// import {
//   Table,
//   TableBody,
//   TableCell,
//   TableHead,
//   TableHeader,
//   TableRow,
// } from "@/components/ui/table";
// import { Button } from "@/components/ui/button";
// import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";

// interface Counts {
//   entered: { [key: string]: number };
//   exited: { [key: string]: number };
//   inside: { [key: string]: number };
// }

// const PeopleCounter = () => {
//   const [counts, setCounts] = useState<Counts>({
//     entered: {},
//     exited: {},
//     inside: {},
//   });
//   const [cameraId, setCameraId] = useState("");
//   const [cameraLink, setCameraLink] = useState("");
//   const [hallId, setHallId] = useState("");
//   const [halls, setHalls] = useState<{ [key: string]: Counts }>({});
//   const [activeTab, setActiveTab] = useState("hall-1"); // Default active tab
//   const socketRef = useRef<any>();

//   useEffect(() => {
//     socketRef.current = io("http://localhost:5000/video", {
//       transports: ["websocket"],
//     });

//     socketRef.current.on("connect", () => {
//       console.log("Connected to server");
//     });

//     socketRef.current.on("video_feed", (data: any) => {
//       const { camera_id, frame } = data;
//       const image = document.getElementById(
//         `camera-${camera_id}`
//       ) as HTMLImageElement;
//       if (image) {
//         image.src = `data:image/jpeg;base64,${frame}`;
//       }
//     });

//     socketRef.current.on("count", (data: any) => {
//       const { count } = data;
//       setHalls(count);
//       setCounts(count[activeTab] || { entered: {}, exited: {}, inside: {} });
//     });

//     axios.get("http://localhost:5000/halls").then((response) => {
//       setHalls(response.data);
//       setCounts(
//         response.data[activeTab] || { entered: {}, exited: {}, inside: {} }
//       );
//     });

//     return () => {
//       if (socketRef.current) {
//         socketRef.current.disconnect();
//       }
//     };
//   }, [activeTab]);

//   const handleAddCamera = (
//     cameraId: string,
//     cameraLink: string,
//     hallId: string
//   ) => {
//     axios
//       .post("http://localhost:5000/add_camera", {
//         camera_id: cameraId,
//         camera_link: cameraLink,
//         hall_id: hallId,
//       })
//       .then((response) => {
//         console.log(response.data);
//         setCameraId("");
//         setCameraLink("");
//         setHallId("");
//       })
//       .catch((error) => {
//         console.error("Error adding camera:", error);
//       });
//   };

//   const handleRemoveCamera = (cameraId: any, hallId: string) => {
//     axios
//       .post("http://localhost:5000/remove_camera", {
//         camera_id: cameraId,
//         hall_id: hallId,
//       })
//       .then((response) => {
//         console.log(response.data);
//       })
//       .catch((error) => {
//         console.error("Error removing camera:", error);
//       });
//   };

//   return (
//     <div className="bg-black">
//       <h1 className="text-3xl font-bold">People Counter</h1>

//       <div className="flex gap-2 flex-col w-1/3">
//         <h2>Add Camera</h2>
//         <input
//           type="text"
//           value={cameraId}
//           onChange={(e) => setCameraId(e.target.value)}
//           placeholder="Camera ID"
//           className="text-white rounded-md px-2 py-1 bg-grey-200 border-gray-200"
//         />
//         <input
//           type="text"
//           value={hallId}
//           onChange={(e) => setHallId(e.target.value)}
//           placeholder="Hall ID"
//           className="text-white rounded-md px-2 py-1 bg-grey-200 border-gray-200"
//         />
//         <input
//           type="text"
//           value={cameraLink}
//           onChange={(e) => setCameraLink(e.target.value)}
//           placeholder="Camera URL"
//           className="text-white rounded-md px-2 py-1 bg-grey-200 border-gray-200"
//         />
//         <button
//           className="bg-white text-black font-bold py-2 px-4 rounded"
//           onClick={() => handleAddCamera(cameraId, cameraLink, hallId)}
//         >
//           Add Camera
//         </button>
//       </div>

//       <Tabs defaultValue={activeTab} className="mt-4">
//         <TabsList>
//           {Object.keys(halls).map((hall) => {
//             const hallCounts = halls[hall] || {
//               entered: {},
//               exited: {},
//               inside: {},
//             };
//             const totalPeopleInsideHall = Object.values(
//               hallCounts.inside || {}
//             ).reduce((sum, count) => sum + count, 0);

//             return (
//               <TabsTrigger key={hall} value={hall}>
//                 Hall {hall} ({totalPeopleInsideHall} people)
//               </TabsTrigger>
//             );
//           })}
//         </TabsList>
//         {Object.keys(halls).map((hall) => (
//           <TabsContent key={hall} value={hall}>
//             <Table className="mt-4 bg-grey-400 rounded-lg border-grey-200 items-center">
//               <TableHeader className="font-bold">
//                 <TableRow>
//                   <TableCell className="w-[100px]">Camera ID</TableCell>
//                   <TableCell>Feed</TableCell>
//                   <TableCell>Entered</TableCell>
//                   <TableCell>Exited</TableCell>
//                   <TableCell>Inside</TableCell>
//                   <TableCell>Actions</TableCell>
//                 </TableRow>
//               </TableHeader>
//               <TableBody>
//                 {Object.keys(halls[hall].entered).map((cameraId) => (
//                   <TableRow key={cameraId}>
//                     <TableCell className="font-medium">{cameraId}</TableCell>
//                     <TableCell>
//                       <img
//                         className="rounded-md"
//                         id={`camera-${cameraId}`}
//                         alt={`Camera ${cameraId}`}
//                         style={{ width: "300px", height: "240px" }}
//                       />
//                     </TableCell>
//                     <TableCell>{halls[hall].entered[cameraId] || 0}</TableCell>
//                     <TableCell>{halls[hall].exited[cameraId] || 0}</TableCell>
//                     <TableCell>{halls[hall].inside[cameraId] || 0}</TableCell>
//                     <TableCell>
//                       <Button
//                         variant={"destructive"}
//                         onClick={() => handleRemoveCamera(cameraId, hall)}
//                       >
//                         Remove
//                       </Button>
//                     </TableCell>
//                   </TableRow>
//                 ))}
//               </TableBody>
//             </Table>
//           </TabsContent>
//         ))}
//       </Tabs>
//     </div>
//   );
// };

// export default PeopleCounter;

import React, { useEffect, useState, useRef } from "react";
import axios from "axios";
import io from "socket.io-client";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Button } from "@/components/ui/button";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";

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
  const [logs, setLogs] = useState<any[]>([]); // State for logs
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
      setCounts(count[activeTab] || { entered: {}, exited: {}, inside: {} });

      // Update logs whenever the count changes
      Object.keys(count).forEach((hall) => {
        Object.keys(count[hall].entered).forEach((cameraId) => {
          const prevEnteredCount = halls[hall]?.entered[cameraId] || 0;
          const prevExitedCount = halls[hall]?.exited[cameraId] || 0;

          if (count[hall].entered[cameraId] > prevEnteredCount) {
            setLogs((prevLogs) => [
              ...prevLogs,
              {
                camera: cameraId,
                hall: hall,
                entered: 1,
                exited: 0,
                inside: count[hall].inside[cameraId],
                time: new Date().toLocaleString(),
              },
            ]);
          }
          if (count[hall].exited[cameraId] > prevExitedCount) {
            setLogs((prevLogs) => [
              ...prevLogs,
              {
                camera: cameraId,
                hall: hall,
                entered: 0,
                exited: 1,
                inside: count[hall].inside[cameraId],
                time: new Date().toLocaleString(),
              },
            ]);
            console.log(logs);
          }
        });
      });
    });

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
  }, [activeTab, halls]); // Include halls in the dependency array

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
    <div className="bg-black min-h-screen text-white">
      <div className="container mx-auto p-4">
        <h1 className="text-3xl font-bold mb-4">People Counter</h1>

        <div className="flex gap-2 flex-col w-full md:w-1/2 lg:w-1/3 mb-4">
          <h2>Add Camera</h2>
          <input
            type="text"
            value={cameraId}
            onChange={(e) => setCameraId(e.target.value)}
            placeholder="Camera ID"
            className="text-black rounded-md px-2 py-1 bg-gray-200 border-gray-200 focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
          <input
            type="text"
            value={hallId}
            onChange={(e) => setHallId(e.target.value)}
            placeholder="Hall ID"
            className="text-black rounded-md px-2 py-1 bg-gray-200 border-gray-200 focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
          <input
            type="text"
            value={cameraLink}
            onChange={(e) => setCameraLink(e.target.value)}
            placeholder="Camera URL"
            className="text-black rounded-md px-2 py-1 bg-gray-200 border-gray-200 focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
          <button
            className="bg-blue-500 hover:bg-blue-700 text-white font-bold py-2 px-4 rounded focus:outline-none focus:ring-2 focus:ring-blue-500"
            onClick={() => handleAddCamera(cameraId, cameraLink, hallId)}
          >
            Add Camera
          </button>
        </div>

        <Tabs defaultValue="halls" className="mb-4">
          <TabsList className="bg-gray-800 rounded-md">
            <TabsTrigger
              value="halls"
              className="text-gray-400 hover:text-white focus:outline-none"
            >
              Halls
            </TabsTrigger>
            <TabsTrigger
              value="logs"
              className="text-gray-400 hover:text-white focus:outline-none"
            >
              Logs
            </TabsTrigger>
          </TabsList>
          <TabsContent value="halls">
            <Tabs defaultValue={activeTab} className="mb-4">
              <TabsList className="bg-gray-800 rounded-md">
                {Object.keys(halls).map((hall) => {
                  const hallCounts = halls[hall] || {
                    entered: {},
                    exited: {},
                    inside: {},
                  };
                  const totalPeopleInsideHall = Object.values(
                    hallCounts.inside || {}
                  ).reduce((sum, count) => sum + count, 0);

                  return (
                    <TabsTrigger
                      key={hall}
                      value={hall}
                      className="text-gray-400 hover:text-white focus:outline-none"
                    >
                      Hall {hall} ({totalPeopleInsideHall} people)
                    </TabsTrigger>
                  );
                })}
              </TabsList>
              {Object.keys(halls).map((hall) => (
                <TabsContent key={hall} value={hall}>
                  <Table className="bg-gray-800 border-collapse">
                    <TableHeader>
                      <TableRow>
                        <TableCell className="w-[100px]">Camera ID</TableCell>
                        <TableCell>Feed</TableCell>
                        <TableCell>Entered</TableCell>
                        <TableCell>Exited</TableCell>
                        <TableCell>Inside</TableCell>
                        <TableCell>Actions</TableCell>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {Object.keys(halls[hall].entered).map((cameraId) => (
                        <TableRow key={cameraId} className="hover:bg-gray-700">
                          <TableCell className="font-medium">
                            {cameraId}
                          </TableCell>
                          <TableCell>
                            <img
                              id={`camera-${cameraId}`}
                              alt={`Camera ${cameraId}`}
                              style={{ width: "400px", height: "300px" }}
                            />
                          </TableCell>
                          <TableCell>
                            {halls[hall].entered[cameraId] || 0}
                          </TableCell>
                          <TableCell>
                            {halls[hall].exited[cameraId] || 0}
                          </TableCell>
                          <TableCell>
                            {halls[hall].inside[cameraId] || 0}
                          </TableCell>
                          <TableCell>
                            <button
                              onClick={() => handleRemoveCamera(cameraId, hall)}
                              className="text-red-500 hover:text-red-700 focus:outline-none"
                            >
                              Remove
                            </button>
                          </TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </TabsContent>
              ))}
            </Tabs>
          </TabsContent>
          <TabsContent value="logs">
            <Table className="mt-4 bg-gray-800 border-collapse">
              <TableHeader>
                <TableRow>
                  <TableCell>Camera</TableCell>
                  <TableCell>Hall</TableCell>
                  <TableCell>Entered</TableCell>
                  <TableCell>Exited</TableCell>
                  <TableCell>Inside</TableCell>
                  <TableCell>Time</TableCell>
                </TableRow>
              </TableHeader>
              <TableBody>
                {logs.map((log, index) => (
                  <TableRow key={index} className="hover:bg-gray-700">
                    <TableCell>{log.camera}</TableCell>
                    <TableCell>{log.hall}</TableCell>
                    <TableCell>{log.entered}</TableCell>
                    <TableCell>{log.exited}</TableCell>
                    <TableCell>{log.inside}</TableCell>
                    <TableCell>{log.time}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </TabsContent>
        </Tabs>
      </div>
    </div>
  );
};

export default PeopleCounter;
