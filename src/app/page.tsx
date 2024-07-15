"use client";
import { useState, useEffect } from "react";
import {
  IoHomeOutline,
  IoCarOutline,
  IoPeopleOutline,
  IoLogOutOutline,
  IoMenuOutline,
} from "react-icons/io5";
import Dashboard from "./components/dashboard";
import ANPR from "./components/anpr";
import PeopleCounter from "./components/people-counter";

type Tab = "Dashboard" | "ANPR" | "PeopleCounter" | "Logout";

export default function Home() {
  const [activeTab, setActiveTab] = useState<Tab>("Dashboard");
  const [isCollapsed, setIsCollapsed] = useState(false);

  useEffect(() => {
    const handleResize = () => {
      if (window.innerWidth < 640) {
        setIsCollapsed(true);
      } else {
        setIsCollapsed(false);
      }
    };

    window.addEventListener("resize", handleResize);

    // Set initial state
    handleResize();

    return () => {
      window.removeEventListener("resize", handleResize);
    };
  }, []);

  const renderContent = () => {
    switch (activeTab) {
      case "Dashboard":
        return <Dashboard />;
      case "ANPR":
        return <ANPR />;
      case "PeopleCounter":
        return <PeopleCounter />;
      default:
        return <Dashboard />;
    }
  };

  const iconMap: Record<Tab, JSX.Element> = {
    Dashboard: <IoHomeOutline className="text-lg" />,
    ANPR: <IoCarOutline className="text-lg" />,
    PeopleCounter: <IoPeopleOutline className="text-lg" />,
    Logout: <IoLogOutOutline className="text-lg" />,
  };

  return (
    <main className="flex min-h-screen flex-row">
      <div
        className={` flex-shrink-0 h-screen border-r border-grey-300 transition-width duration-300 ease-in-out`}
        style={{
          backgroundColor: "#141414",
          width: isCollapsed ? "52px" : "200px",
        }}
      >
        <div className="flex items-center justify-between px-4 py-3">
          {!isCollapsed && (
            <h1 className="text-xl font-bold text-white">BlackCat.id</h1>
          )}
          <button
            onClick={() => setIsCollapsed(!isCollapsed)}
            className="text-white"
          >
            <IoMenuOutline className="text-lg" />
          </button>
        </div>
        <div className="flex flex-col pt-8 gap-2">
          {(["Dashboard", "ANPR", "PeopleCounter", "Logout"] as Tab[]).map(
            (tab) => (
              <div
                key={tab}
                className={`flex items-center rounded-md ${
                  activeTab === tab ? "bg-white" : "border border-grey-400"
                } transition duration-500 ease-in-out hover:border-grey-200 hover:cursor-pointer hover:duration-500`}
                style={{
                  marginInline: "8px",
                  // borderColor: activeTab === tab ? "white" : "#141414",
                }}
                onClick={() => setActiveTab(tab)}
              >
                <span
                  className={`p-1 pl-2 font-semibold flex items-center ${
                    activeTab === tab ? "text-black" : "text-white"
                  }`}
                >
                  {iconMap[tab]}
                  {!isCollapsed && (
                    <span className="ml-2">
                      {tab === "PeopleCounter" ? "People Counter" : tab}
                    </span>
                  )}
                </span>
              </div>
            )
          )}
        </div>
      </div>
      <div className="flex-grow p-4">{renderContent()}</div>
    </main>
  );
}
