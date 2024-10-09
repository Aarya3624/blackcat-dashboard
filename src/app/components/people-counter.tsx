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
        const response = await fetch("http://127.0.0.1:5000/count");
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

  return <div></div>;
};

export default PeopleCounter;
