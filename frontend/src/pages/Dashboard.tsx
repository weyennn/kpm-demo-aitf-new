import { useEffect } from "react";
import api from "../services/api";

function Dashboard() {

  useEffect(() => {
    api.get("/health")
      .then(res => {
        console.log(res.data);
      })
      .catch(err => {
        console.error(err);
      });
  }, []);

  return (
    <div>
      <h1>Dashboard</h1>
    </div>
  );
}

export default Dashboard;