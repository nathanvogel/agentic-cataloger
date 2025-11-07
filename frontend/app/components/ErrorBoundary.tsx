import React, { useEffect } from "react";
import { useRouteError } from "react-router";
import { Typography } from "@mui/material";
import { styled } from "@mui/material/styles";

const ErrorContainer = styled("div")`
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  min-height: 100vh;
`;

const ErrorDetail = styled("pre")`
  max-width: 800px;
  overflow: auto;
  border-radius: 12px;
  margin-bottom: 48px;
`;

export const ErrorBoundaryRoute: React.FC = () => {
  const error = useRouteError() as Error;
  useEffect(() => {
    if (error) {
      // TODO: Send to Sentry.
      // eslint-disable-next-line no-console
      console.error(error);
    }
  }, [error]);

  return (
    <ErrorContainer>
      <Typography variant="h3">Something went wrong</Typography>

      {error && <ErrorDetail>{error.message || "Unknown error"}</ErrorDetail>}

      <a href="/">Back to the homepage</a>
    </ErrorContainer>
  );
};

type ErrorBoundaryRootProps = {
  message: string;
  details: string;
  stack: string;
};

export const ErrorBoundaryRoot: React.FC<ErrorBoundaryRootProps> = ({
  message,
  details,
  stack,
}) => {
  useEffect(() => {
    if (message) {
      // eslint-disable-next-line no-console
      console.error(message, details, stack);
    }
  }, [message, details, stack]);

  return (
    <ErrorContainer>
      <Typography variant="h3">Something went wrong</Typography>

      {(message || details || stack) && (
        <ErrorDetail>{`${message} ${details} ${stack}`}</ErrorDetail>
      )}

      <a href="/">Back to the homepage</a>
    </ErrorContainer>
  );
};
