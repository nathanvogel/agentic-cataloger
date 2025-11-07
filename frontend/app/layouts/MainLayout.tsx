import React from "react";
import { Outlet } from "react-router";
import { Box } from "@mui/material";
import Footer from "./components/Footer";
import Header from "./components/Header";

export const MainLayout: React.FC = () => {
  return (
    <Box
      sx={{
        display: "flex",
        flexDirection: "column",
        minHeight: "100vh",
      }}
    >
      <Header />
      <Box component="main" sx={{ flex: 1, py: 4, px: 2 }}>
        <Outlet />
      </Box>
      <Footer />
    </Box>
  );
};
