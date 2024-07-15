import React from "react";

const Dashboard = () => {
  return (
    <div className="flex flex-col w-full gap-2 h-full">
      <h1 className="text-3xl font-bold">Dashboard</h1>

      <p className="text-xs text-gray-400">Welcome to your dashboard!</p>

      <div className="flex bg-grey-400 border border-grey-300 p-5 justify-center items-center w-2/3 mt-1 rounded-md flex-grow">
        <div className="font-bold">Video feed</div>
      </div>
      <div
        className="flex bg-grey-400 border border-grey-300 p-5 justify-center items-center w-2/3 mt-1 rounded-md"
        style={{
          height: "140px",
        }}
      >
        <div>Footer</div>
      </div>
    </div>
  );
};

export default Dashboard;
