// import { useState } from 'react'
// import reactLogo from './assets/react.svg'
// import viteLogo from '/vite.svg'
// import './App.css'

// function App() {
//   const [count, setCount] = useState(0)

//   return (
//     <>
//       <div>
//         <a href="https://vite.dev" target="_blank">
//           <img src={viteLogo} className="logo" alt="Vite logo" />
//         </a>
//         <a href="https://react.dev" target="_blank">
//           <img src={reactLogo} className="logo react" alt="React logo" />
//         </a>
//       </div>
//       <h1>Vite + React</h1>
//       <div className="card">
//         <button onClick={() => setCount((count) => count + 1)}>
//           count is {count}
//         </button>
//         <p>
//           Edit <code>src/App.tsx</code> and save to test HMR
//         </p>
//       </div>
//       <p className="read-the-docs">
//         Click on the Vite and React logos to learn more
//       </p>
//     </>
//   )
// }

// export default App

// import { BrowserRouter, Routes, Route } from "react-router-dom";
// // import Login from "./pages/Login";
// import Dashboard from "./pages/Dashboard";

// function App() {
//   return (
//     <BrowserRouter>
//       <Routes>
//         {/* <Route path="/" element={<Login />} /> */}
//         <Route path="/dashboard" element={<Dashboard />} />
//       </Routes>
//     </BrowserRouter>
//   );
// }

// export default App;

// versi bisa
import { useEffect } from "react";
import api from "./services/api";
import type { AxiosResponse } from "axios";

function Dashboard() {

  useEffect(() => {
    api.get("/health")
      .then((res: AxiosResponse) => {
        console.log("DATA DARI BACKEND:", res.data);
      })
      .catch((err) => {
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

