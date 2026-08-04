import React from "react";
import { Box, Link } from "@mui/material";

const links = [
  {
    label: "Privacy",
    href: "/privacy",
  },
  {
    label: "Terms",
    href: "/terms",
  },
  {
    label: "Imprint",
    href: "/imprint",
  },
];

const year = new Date().getFullYear();

const Footer: React.FC = () => {
  return (
    <Box
      component="footer"
      sx={{
        py: 3,
        px: 2,
        mt: "auto",
        textAlign: "center",
        borderTop: 1,
        borderColor: "divider",
      }}
    >
      <Box sx={{ display: "flex", justifyContent: "center", gap: 3, mb: 1 }}>
        {links.map((link) => (
          <Link
            key={link.href}
            href={link.href}
            underline="hover"
            color="text.secondary"
          >
            {link.label}
          </Link>
        ))}
      </Box>
      <Box sx={{ color: "text.secondary", fontSize: "0.875rem" }}>
        © {year} Nathan Vogel
      </Box>
    </Box>
  );
};

export default Footer;
