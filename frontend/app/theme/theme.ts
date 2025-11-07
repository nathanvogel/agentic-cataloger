import { createTheme } from "@mui/material/styles";

declare module "@mui/material/styles" {
  interface CommonColors {
    glass: {
      light: string;
      dark: string;
    };
  }
}

export const green = "#034910ff";
export const white = "#FFFFFF";
export const black = "#000000";

const breakpoints = {
  values: {
    xs: 0,
    sm: 600,
    md: 900,
    lg: 1200,
    xl: 1536,
  },
};

export const theme = createTheme({
  breakpoints: breakpoints,
  palette: {
    primary: {
      main: green,
    },
  },
  typography: {
    fontFamily: '"Inter", sans-serif',
  },
});

export type Theme = typeof theme;
